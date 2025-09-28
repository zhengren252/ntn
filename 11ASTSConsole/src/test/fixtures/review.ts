/*
 * Review Flow API fixtures for Playwright route mocking
 * Provide stable, reusable payloads for review and approval endpoints
 */

export type ReviewItem = {
  id: string;
  strategyName: string;
  submittedBy: string;
  submittedAt: string;
  status: 'pending' | 'approved' | 'rejected';
  riskLevel: 'low' | 'medium' | 'high';
  description: string;
};

export type ReviewListResponse = {
  code: number;
  message: string;
  data: {
    reviews: ReviewItem[];
    total: number;
    page: number;
    pageSize: number;
  };
};

export type ReviewActionResponse = {
  code: number;
  message: string;
  data: {
    success: boolean;
    reviewId: string;
    newStatus: string;
  };
};

export function makeReviewListResponse(): ReviewListResponse {
  return {
    code: 0,
    message: 'ok',
    data: {
      reviews: [
        {
          id: 'review_001',
          strategyName: '均线突破策略v2.1',
          submittedBy: '策略开发团队',
          submittedAt: new Date(Date.now() - 3600000).toISOString(),
          status: 'pending',
          riskLevel: 'medium',
          description: '基于双均线交叉的改进策略，增加了风险控制模块'
        },
        {
          id: 'review_002',
          strategyName: '网格交易策略',
          submittedBy: '量化研究部',
          submittedAt: new Date(Date.now() - 7200000).toISOString(),
          status: 'pending',
          riskLevel: 'low',
          description: '适用于震荡市场的网格交易策略，回撤控制良好'
        }
      ],
      total: 2,
      page: 1,
      pageSize: 10
    }
  };
}

export function makeReviewActionResponse(reviewId: string, action: 'approve' | 'reject'): ReviewActionResponse {
  return {
    code: 0,
    message: 'ok',
    data: {
      success: true,
      reviewId,
      newStatus: action === 'approve' ? 'approved' : 'rejected'
    }
  };
}