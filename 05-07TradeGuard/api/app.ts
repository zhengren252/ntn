/**
 * This is a API server
 */

import express, { type Request, type Response }  from 'express';
import cors from 'cors';

import dotenv from 'dotenv';

import authRoutes from './routes/auth.js';

// for esm mode


// load env
dotenv.config();


const app: express.Application = express();

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

/**
 * API Routes
 */
app.use('/api/auth', authRoutes);

/**
 * health
 */
app.use('/api/health', (req: Request, res: Response) => {
  res.status(200).json({
    success: true,
    message: 'ok'
  });
});

// 标准化根路径健康检查端点（用于 Docker/Compose 健康检查）
app.get('/health', (req: Request, res: Response): void => {
  res.status(200).json({ status: 'healthy' });
});
app.get('/live', (req: Request, res: Response): void => {
  res.status(200).json({ status: 'alive' });
});

/**
 * error handler middleware
 */
app.use((error: Error, req: Request, res: Response, next: express.NextFunction) => {
  res.status(500).json({
    success: false,
    error: 'Server internal error'
  });
});

/**
 * 404 handler
 */
app.use((req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: 'API not found'
  });
});

export default app;