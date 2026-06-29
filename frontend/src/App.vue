<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { generateReview, notifyWeCom } from './api';

const feelings = ['服务好', '出餐快', '环境干净', '饮品颜值高', '甜度合适', '店员耐心'];

const platformOptions = {
  google: {
    label: 'Google',
    hint: '英文评价',
    editorLabel: '评价正文',
    placeholder: '真实模型生成的 Google 评价会显示在这里，也可以直接输入或修改。',
    generationHint: 'AI 生成会控制在 45-75 个英文词左右，用于减少 token 消耗；手动修改不限长度。',
    url: 'https://www.google.com/maps/search/?api=1&query=Sunny%20Tea%20House%20San%20Jose',
  },
  xiaohongshu: {
    label: '小红书',
    hint: '推荐文案',
    editorLabel: '推荐文案',
    placeholder: '真实模型生成的小红书推荐文案会显示在这里，也可以直接输入或修改。',
    generationHint: 'AI 生成会控制在 80-140 个中文字符左右，用于减少 token 消耗；手动修改不限长度。',
    url: 'https://www.xiaohongshu.com/explore',
  },
};

const draftStorageKey = 'sunny-tea-review-demo-draft';

const selectedFeelings = ref([]);
const platform = ref('google');
const reviewText = ref('');
const webhookPreview = ref(null);
const hasGeneratedReview = ref(false);
const isGenerating = ref(false);
const isContinuing = ref(false);
const notice = ref('');
const noticeTone = ref('neutral');
const manualCopyNeeded = ref(false);

const canGenerate = computed(
  () =>
    selectedFeelings.value.length >= 1 &&
    selectedFeelings.value.length <= 2 &&
    !isGenerating.value &&
    !hasGeneratedReview.value,
);

const hasReview = computed(() => reviewText.value.trim().length > 0);
const canOpenPlatform = computed(() => hasReview.value && !isGenerating.value && !isContinuing.value);
const currentPlatformOption = computed(() => platformOptions[platform.value]);
const reviewLength = computed(() => Array.from(reviewText.value).length);
const webhookJson = computed(() =>
  webhookPreview.value ? JSON.stringify(webhookPreview.value.request.body, null, 2) : '',
);

function setNotice(message, tone = 'neutral') {
  notice.value = message;
  noticeTone.value = tone;
}

function resetTransientState() {
  isGenerating.value = false;
  isContinuing.value = false;
  manualCopyNeeded.value = false;
}

function handleReviewInput() {
  webhookPreview.value = null;
  manualCopyNeeded.value = false;
  saveDraftState();
}

function saveDraftState() {
  if (!hasReview.value && selectedFeelings.value.length === 0 && !webhookPreview.value) {
    return;
  }

  try {
    window.sessionStorage.setItem(
      draftStorageKey,
      JSON.stringify({
        selectedFeelings: selectedFeelings.value,
        platform: platform.value,
        reviewText: reviewText.value,
        webhookPreview: webhookPreview.value,
        hasGeneratedReview: hasGeneratedReview.value,
      }),
    );
  } catch {
    // Session storage can be unavailable in strict browser privacy modes.
  }
}

function restoreDraftState() {
  try {
    const rawDraft = window.sessionStorage.getItem(draftStorageKey);
    if (!rawDraft) {
      return;
    }

    const draft = JSON.parse(rawDraft);
    if (Array.isArray(draft.selectedFeelings)) {
      selectedFeelings.value = draft.selectedFeelings
        .filter((feeling) => feelings.includes(feeling))
        .slice(0, 2);
    }
    if (draft.platform && platformOptions[draft.platform]) {
      platform.value = draft.platform;
    }
    if (typeof draft.reviewText === 'string') {
      reviewText.value = draft.reviewText;
    }
    if (draft.webhookPreview && typeof draft.webhookPreview === 'object') {
      webhookPreview.value = draft.webhookPreview;
    }
    hasGeneratedReview.value = Boolean(draft.hasGeneratedReview);
  } catch {
    try {
      window.sessionStorage.removeItem(draftStorageKey);
    } catch {
      // Ignore storage cleanup failures for the same reason as read failures.
    }
  }
}

function handlePageShow() {
  restoreDraftState();
  resetTransientState();
}

onMounted(() => {
  restoreDraftState();
  window.addEventListener('pageshow', handlePageShow);
  window.addEventListener('pagehide', saveDraftState);
});

onBeforeUnmount(() => {
  window.removeEventListener('pageshow', handlePageShow);
  window.removeEventListener('pagehide', saveDraftState);
});

function toggleFeeling(feeling) {
  if (hasGeneratedReview.value) {
    setNotice('已生成一次，感受标签已锁定，请直接修改正文。', 'warning');
    return;
  }

  manualCopyNeeded.value = false;
  webhookPreview.value = null;
  const next = [...selectedFeelings.value];
  const index = next.indexOf(feeling);
  if (index >= 0) {
    next.splice(index, 1);
    selectedFeelings.value = next;
    return;
  }
  if (next.length >= 2) {
    setNotice('最多选择 2 个感受。', 'warning');
    return;
  }
  next.push(feeling);
  selectedFeelings.value = next;
  setNotice('');
}

function selectPlatform(nextPlatform) {
  if (hasGeneratedReview.value) {
    setNotice('已生成一次，发布平台已锁定，请直接修改正文。', 'warning');
    return;
  }

  platform.value = nextPlatform;
  webhookPreview.value = null;
  manualCopyNeeded.value = false;
  saveDraftState();
  setNotice('');
}

async function handleGenerate() {
  if (hasGeneratedReview.value) {
    setNotice('已生成一次，不能再次生成，请直接手动修改正文。', 'warning');
    return;
  }

  if (!canGenerate.value) {
    setNotice('请先选择 1-2 个感受。', 'warning');
    return;
  }

  isGenerating.value = true;
  manualCopyNeeded.value = false;
  webhookPreview.value = null;
  setNotice('正在调用真实模型生成评价...', 'neutral');

  try {
    const result = await generateReview({
      feelings: selectedFeelings.value,
      platform: platform.value,
    });
    reviewText.value = result.text;
    hasGeneratedReview.value = true;
    saveDraftState();
    setNotice('内容已生成，后续只能手动修改。', 'success');
  } catch (error) {
    setNotice(error.message || '生成失败，请重试。', 'error');
  } finally {
    isGenerating.value = false;
  }
}

async function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await Promise.race([
        navigator.clipboard.writeText(text),
        new Promise((_, reject) => {
          window.setTimeout(() => reject(new Error('Clipboard timeout')), 800);
        }),
      ]);
      return true;
    } catch {
      // Continue to the legacy fallback below.
    }
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.top = '-999px';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);
  return copied;
}

async function handleCopyAndContinue() {
  const text = reviewText.value.trim();
  if (!text) {
    setNotice('请先生成或输入评价内容。', 'warning');
    return;
  }

  isContinuing.value = true;
  manualCopyNeeded.value = false;

  try {
    const copied = await copyToClipboard(text);
    if (!copied) {
      manualCopyNeeded.value = true;
      setNotice('浏览器限制了剪贴板权限，已继续模拟 Webhook。', 'warning');
    }

    if (copied) {
      setNotice('已复制，正在模拟拼装企业微信 Webhook...', 'neutral');
    }
    let wecomMessage = 'Webhook 模拟调用完成，下面可查看请求体。';
    let wecomTone = 'success';
    try {
      const result = await notifyWeCom({
        review: text,
        platform: platform.value,
        feelings: selectedFeelings.value,
      });
      webhookPreview.value = result;
      saveDraftState();
      if (!result.sent) {
        wecomMessage = '已复制；Webhook 模拟返回未发送。';
        wecomTone = 'warning';
      }
    } catch (error) {
      wecomMessage = `已复制；Webhook 模拟失败：${error.message}`;
      wecomTone = 'warning';
    }

    setNotice(wecomMessage, wecomTone);
  } catch (error) {
    manualCopyNeeded.value = true;
    setNotice(error.message || '复制失败，请手动复制文本。', 'error');
  } finally {
    isContinuing.value = false;
  }
}

function openPlatformEntry() {
  resetTransientState();
  saveDraftState();
  window.location.assign(platformOptions[platform.value].url);
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Sunny Tea House</p>
        <h1>AI 评价生成</h1>
      </div>
      <span class="status-pill">真实模型 + 模拟</span>
    </header>

    <section class="step-panel" aria-labelledby="feelings-title">
      <div class="section-heading">
        <span class="step-index">1</span>
        <div>
          <h2 id="feelings-title">消费感受</h2>
          <p>{{ selectedFeelings.length }}/2 selected</p>
        </div>
      </div>
      <div class="chip-grid" role="group" aria-label="消费感受">
        <button
          v-for="feeling in feelings"
          :key="feeling"
          type="button"
          class="chip"
          :class="{ selected: selectedFeelings.includes(feeling) }"
          :disabled="hasGeneratedReview"
          :aria-pressed="selectedFeelings.includes(feeling)"
          @click="toggleFeeling(feeling)"
        >
          {{ feeling }}
        </button>
      </div>
    </section>

    <section class="step-panel" aria-labelledby="platform-title">
      <div class="section-heading">
        <span class="step-index">2</span>
        <div>
          <h2 id="platform-title">发布平台</h2>
          <p>{{ platformOptions[platform].hint }}</p>
        </div>
      </div>
      <div class="segmented" role="tablist" aria-label="发布平台">
        <button
          v-for="(option, key) in platformOptions"
          :key="key"
          type="button"
          role="tab"
          class="segment"
          :class="{ active: platform === key }"
          :disabled="hasGeneratedReview"
          :aria-selected="platform === key"
          @click="selectPlatform(key)"
        >
          {{ option.label }}
        </button>
      </div>
    </section>

    <section class="step-panel" aria-labelledby="copy-title">
      <div class="section-heading">
        <span class="step-index">3</span>
        <div>
          <h2 id="copy-title">生成与编辑</h2>
          <p>{{ platform === 'google' ? '自然英文评价' : '中文种草风格' }}</p>
        </div>
      </div>

      <button type="button" class="primary-action" :disabled="!canGenerate" @click="handleGenerate">
        {{ hasGeneratedReview ? '已生成，请手动修改' : isGenerating ? '生成中...' : '生成内容' }}
      </button>

      <label class="editor-label" for="review-editor">{{ currentPlatformOption.editorLabel }}</label>
      <textarea
        id="review-editor"
        v-model="reviewText"
        class="review-editor"
        rows="9"
        :placeholder="currentPlatformOption.placeholder"
        @input="handleReviewInput"
      />
      <div class="length-meter">
        {{ currentPlatformOption.generationHint }} 当前正文 {{ reviewLength }} 字
      </div>

      <div v-if="manualCopyNeeded" class="manual-copy">
        剪贴板不可用，请长按文本框选择复制。
      </div>

      <button
        type="button"
        class="continue-action"
        :disabled="!hasReview || isContinuing"
        @click="handleCopyAndContinue"
      >
        {{ isContinuing ? '处理中...' : '复制并模拟 Webhook' }}
      </button>

      <button type="button" class="secondary-action" :disabled="!canOpenPlatform" @click="openPlatformEntry">
        打开发布入口
      </button>
    </section>

    <section v-if="webhookPreview" class="step-panel" aria-labelledby="webhook-title">
      <div class="section-heading">
        <span class="step-index">4</span>
        <div>
          <h2 id="webhook-title">Webhook 演示</h2>
          <p>前端演示请求拼装，不发送真实企微</p>
        </div>
      </div>

      <div class="webhook-summary">
        <p><strong>请求方式</strong>{{ webhookPreview.request.method }}</p>
        <p><strong>演示地址</strong>{{ webhookPreview.request.url }}</p>
        <p><strong>中文摘要</strong>{{ webhookPreview.summary }}</p>
        <p><strong>回复草稿</strong>{{ webhookPreview.replyDraft }}</p>
      </div>

      <label class="editor-label" for="webhook-json">Webhook 请求体</label>
      <pre id="webhook-json" class="webhook-json">{{ webhookJson }}</pre>
    </section>

    <p v-if="notice" class="notice" :class="noticeTone" role="status">
      {{ notice }}
    </p>
  </main>
</template>
