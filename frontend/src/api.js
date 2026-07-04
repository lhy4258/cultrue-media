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

async function postStream(path, payload, onChunk) {
  let response;
  try {
    response = await fetch(apiUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error(toFriendlyError(error.message || 'Failed to fetch'));
  }

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

  if (!response.body) {
    throw new Error('浏览器不支持流式读取，请稍后重试。');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';

  function handleEventBlock(block) {
    const lines = block.split('\n');
    const eventLine = lines.find((line) => line.startsWith('event:'));
    const dataLines = lines.filter((line) => line.startsWith('data:'));
    const eventName = eventLine ? eventLine.replace('event:', '').trim() : 'message';
    const rawData = dataLines.map((line) => line.replace('data:', '').trim()).join('\n');

    if (!rawData) {
      return;
    }

    let data;
    try {
      data = JSON.parse(rawData);
    } catch {
      throw new Error('模型流式响应格式错误，请稍后重试。');
    }

    if (eventName === 'chunk') {
      const chunk = typeof data.text === 'string' ? data.text : '';
      if (chunk) {
        fullText += chunk;
        onChunk(chunk, fullText);
      }
      return;
    }

    if (eventName === 'error') {
      throw new Error(toFriendlyError(data.message || '生成失败，请重试。'));
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replace(/\r\n/g, '\n');

      let boundary = buffer.indexOf('\n\n');
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary).trim();
        buffer = buffer.slice(boundary + 2);
        if (block) {
          handleEventBlock(block);
        }
        boundary = buffer.indexOf('\n\n');
      }

      if (done) {
        break;
      }
    }

    const finalBlock = buffer.trim();
    if (finalBlock) {
      handleEventBlock(finalBlock);
    }
  } finally {
    reader.releaseLock();
  }

  const text = fullText.trim();
  if (!text) {
    throw new Error('模型返回内容为空，请稍后重试或检查模型配置。');
  }
  return {
    text,
    platform: payload.platform,
  };
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

export async function generateReview(payload) {
  const result = await postJson('/api/generate-review', payload);
  const text = typeof result.text === 'string' ? result.text.trim() : '';
  if (!text) {
    throw new Error('模型返回内容为空，请稍后重试或检查模型配置。');
  }
  return {
    ...result,
    text,
  };
}

export async function streamReview(payload, onChunk) {
  return postStream('/api/generate-review-stream', payload, onChunk);
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
