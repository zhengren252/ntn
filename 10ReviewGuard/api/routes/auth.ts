/**
 * This is a user authentication API route demo.
 * Handle user registration, login, token management, etc.
 */
import { Router, type Request, type Response, type NextFunction } from 'express';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import rateLimit from 'express-rate-limit';

const router = Router();

// JWT配置
const JWT_SECRET = process.env.JWT_SECRET || 'reviewguard-secret-key';
const JWT_EXPIRES_IN = '24h';

// 内存存储（生产环境应使用数据库）
interface User {
  id: string;
  username: string;
  email: string;
  password_hash: string;
  role: string;
  created_at: Date;
}

interface Session {
  token: string;
  user_id: string;
  expires_at: Date;
}

const users: Map<string, User> = new Map();
const sessions: Map<string, Session> = new Map();

// 登录限流
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15分钟
  max: 5, // 最多5次尝试
  message: {
    error: 'Too many login attempts',
    message: '登录尝试次数过多，请15分钟后重试'
  }
});

// 认证中间件
export async function authenticateToken(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({
      error: 'Access token required',
      message: '需要提供访问令牌'
    });
  }

  try {
    const session = sessions.get(token);
    if (!session || session.expires_at < new Date()) {
      sessions.delete(token);
      return res.status(403).json({
        error: 'Invalid or expired token',
        message: '令牌无效或已过期'
      });
    }

    const user = users.get(session.user_id);
    if (!user) {
      return res.status(403).json({
        error: 'User not found',
        message: '用户不存在'
      });
    }

    (req as any).user = user;
    next();
  } catch (error) {
    console.error('Token verification error:', error);
    return res.status(500).json({
      error: 'Token verification failed',
      message: '令牌验证失败'
    });
  }
}

/**
 * User Registration
 * POST /api/auth/register
 */
router.post('/register', async (req: Request, res: Response): Promise<void> => {
  try {
    const { username, email, password, role = 'user' } = req.body;

    if (!username || !email || !password) {
      res.status(400).json({
        error: 'Missing required fields',
        message: '用户名、邮箱和密码不能为空'
      });
      return;
    }

    // 检查用户名是否已存在
    const existingUser = Array.from(users.values()).find(u => u.username === username);
    if (existingUser) {
      res.status(409).json({
        error: 'Username already exists',
        message: '用户名已存在'
      });
      return;
    }

    // 检查邮箱是否已存在
    const existingEmail = Array.from(users.values()).find(u => u.email === email);
    if (existingEmail) {
      res.status(409).json({
        error: 'Email already exists',
        message: '邮箱已存在'
      });
      return;
    }

    // 密码哈希
    const password_hash = await bcrypt.hash(password, 10);
    const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const newUser: User = {
      id: userId,
      username,
      email,
      password_hash,
      role,
      created_at: new Date()
    };

    users.set(userId, newUser);

    res.status(201).json({
      success: true,
      message: '用户注册成功',
      data: { id: userId }
    });
  } catch (error) {
    console.error('Register error:', error);
    res.status(500).json({
      error: 'Registration failed',
      message: '注册失败，请稍后重试'
    });
  }
});

/**
 * User Login
 * POST /api/auth/login
 */
router.post('/login', loginLimiter, async (req: Request, res: Response): Promise<void> => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      res.status(400).json({
        error: 'Missing credentials',
        message: '用户名和密码不能为空'
      });
      return;
    }

    // 查找用户
    const user = Array.from(users.values()).find(u => u.username === username);
    if (!user) {
      res.status(401).json({
        error: 'Invalid credentials',
        message: '用户名或密码错误'
      });
      return;
    }

    // 验证密码
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      res.status(401).json({
        error: 'Invalid credentials',
        message: '用户名或密码错误'
      });
      return;
    }

    // 生成JWT令牌
    const token = jwt.sign(
      { userId: user.id, username: user.username },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    // 创建会话
    const session: Session = {
      token,
      user_id: user.id,
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000) // 24小时
    };
    sessions.set(token, session);

    res.json({
      success: true,
      message: '登录成功',
      data: {
        user: {
          id: user.id,
          username: user.username,
          email: user.email,
          role: user.role
        },
        token,
        expires_in: 24 * 60 * 60
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({
      error: 'Login failed',
      message: '登录失败，请稍后重试'
    });
  }
});

/**
 * User Logout
 * POST /api/auth/logout
 */
router.post('/logout', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (token) {
      sessions.delete(token);
    }

    res.json({
      success: true,
      message: '登出成功'
    });
  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({
      error: 'Logout failed',
      message: '登出失败'
    });
  }
});

// 获取当前用户信息
router.get('/me', authenticateToken, async (req: Request, res: Response) => {
  try {
    const user = (req as any).user;
    
    res.json({
      success: true,
      data: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        created_at: user.created_at
      }
    });
  } catch (error) {
    console.error('Get user info error:', error);
    res.status(500).json({
      error: 'Failed to get user info',
      message: '获取用户信息失败'
    });
  }
});

export default router;