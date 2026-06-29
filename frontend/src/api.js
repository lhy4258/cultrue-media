const MOCK_WEBHOOK_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=MOCK_DEMO_KEY';
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const platformNames = {
  google: 'Google',
  xiaohongshu: '小红书',
};

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

function wait(ms = 500) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function postJson(path, payload) {
  const response = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || data.error || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(toFriendlyError(message));
  }

  return response.json();
}

function toFriendlyError(message) {
  if (message.includes('LLM_API_KEY is not configured')) {
    return '后端未配置 LLM_API_KEY，请在 backend/.env 中填写模型密钥后重试。';
  }
  if (message.includes('Network error')) {
    return '后端调用模型失败，请检查网络、模型地址或 API Key。';
  }
  if (message.includes('Failed to fetch')) {
    return '无法连接后端服务，请先启动 FastAPI 后端。';
  }
  return message;
}

function normalizeFeelings(feelings) {
  return feelings.filter((item) => typeof item === 'string' && item.trim()).slice(0, 2);
}

function summarizeReview(review, platform, feelings) {
  const platformName = platformNames[platform] || platform;
  const feelingText = feelings.length ? `，重点感受是${feelings.join('、')}` : '';
  return `顾客在 ${platformName} 的评价整体偏正向${feelingText}。`;
}

function buildReplyDraft(platform, feelings) {
  const feelingText = feelings.length ? `对${feelings.join('、')}的认可` : '反馈';
  const platformName = platformNames[platform] || platform;
  return `感谢您在 ${platformName} 分享体验，也谢谢您${feelingText}。我们会继续保持饮品品质和服务细节，欢迎下次再来。`;
}

function buildWebhookMarkdown({ review, platform, feelings, summary, replyDraft }) {
  const platformName = platformNames[platform] || platform;
  const feelingText = feelings.length ? feelings.join('、') : '未选择';
  return [
    '## Sunny Tea House 新评价提醒',
    `> 平台：${platformName}`,
    `> 感受：${feelingText}`,
    '',
    `**中文摘要**：${summary}`,
    '',
    `**商家回复草稿**：${replyDraft}`,
    '',
    '**顾客评价原文**',
    review.trim(),
  ].join('\n');
}

export function buildWeComWebhookRequest({ review, platform, feelings }) {
  const normalizedFeelings = normalizeFeelings(feelings);
  const summary = summarizeReview(review, platform, normalizedFeelings);
  const replyDraft = buildReplyDraft(platform, normalizedFeelings);
  const body = {
    msgtype: 'markdown',
    markdown: {
      content: buildWebhookMarkdown({
        review,
        platform,
        feelings: normalizedFeelings,
        summary,
        replyDraft,
      }),
    },
  };

  return {
    url: MOCK_WEBHOOK_URL,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    summary,
    replyDraft,
  };
}

export function generateReview(payload) {
  return postJson('/api/generate-review', payload);
}

export async function notifyWeCom(payload) {
  const request = buildWeComWebhookRequest(payload);
  await wait(550);
  return {
    sent: true,
    mode: 'mock',
    summary: request.summary,
    replyDraft: request.replyDraft,
    request,
  };
}
