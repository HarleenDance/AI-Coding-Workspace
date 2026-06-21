<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/stores/app'
import type { ModelConfigCreate } from '@/api'
import { ElMessage } from 'element-plus'

const store = useAppStore()

const showCreate = ref(false)
const testing = ref(false)
const formData = ref<ModelConfigCreate>({
  name: '',
  provider: 'deepseek',
  base_url: 'https://api.deepseek.com',
  api_key: '',
  chat_model: '',
  reasoner_model: '',
  temperature: 0.3,
  max_tokens: 4096,
  is_default: false,
})

const providerPresets: Record<string, { base_url: string; chat_model: string; reasoner_model: string }> = {
  deepseek: { base_url: 'https://api.deepseek.com', chat_model: 'deepseek-chat', reasoner_model: 'deepseek-reasoner' },
  qwen: { base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', chat_model: 'qwen-plus', reasoner_model: 'qwen-max' },
  moonshot: { base_url: 'https://api.moonshot.cn/v1', chat_model: 'moonshot-v1-8k', reasoner_model: 'moonshot-v1-32k' },
  glm: { base_url: 'https://open.bigmodel.cn/api/paas/v4', chat_model: 'glm-4-flash', reasoner_model: 'glm-4' },
  openai: { base_url: 'https://api.openai.com/v1', chat_model: 'gpt-4o-mini', reasoner_model: 'gpt-4o' },
}

function onProviderChange(provider: string) {
  const preset = providerPresets[provider]
  if (preset) {
    formData.value.base_url = preset.base_url
    formData.value.chat_model = preset.chat_model
    formData.value.reasoner_model = preset.reasoner_model
  }
}

function selectModel(id: string) {
  store.currentModelId = id
}

function openCreate() {
  formData.value = {
    name: '',
    provider: 'deepseek',
    base_url: 'https://api.deepseek.com',
    api_key: '',
    chat_model: 'deepseek-chat',
    reasoner_model: '',
    temperature: 0.3,
    max_tokens: 4096,
    is_default: false,
  }
  showCreate.value = true
}

async function submitCreate() {
  if (!formData.value.name || !formData.value.api_key || !formData.value.chat_model) {
    ElMessage.warning('请填写名称、API Key 和模型名')
    return
  }
  await store.createModel(formData.value)
  showCreate.value = false
}

async function testCurrentModel() {
  if (!store.currentModelId) return
  testing.value = true
  try {
    await store.testModel(store.currentModelId)
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div class="model-selector">
    <el-select
      :model-value="store.currentModelId"
      size="small"
      class="model-select"
      @change="selectModel"
    >
      <template #prefix>
        <el-icon><Cpu /></el-icon>
      </template>
      <el-option
        v-for="model in store.models"
        :key="model.id"
        :value="model.id"
        :label="model.name"
      >
        <div class="model-option">
          <span class="model-name">{{ model.name }}</span>
          <span class="model-detail">{{ model.chat_model }}</span>
          <el-tag v-if="model.is_default" size="small" type="success">默认</el-tag>
          <el-tag v-if="model.is_builtin" size="small" type="info">内置</el-tag>
        </div>
      </el-option>
    </el-select>

    <el-tooltip content="测试连通性" placement="bottom">
      <el-button text size="small" :loading="testing" @click="testCurrentModel">
        <el-icon><Connection /></el-icon>
      </el-button>
    </el-tooltip>

    <el-tooltip content="添加模型" placement="bottom">
      <el-button text size="small" class="add-btn" @click="openCreate">
        <el-icon><Plus /></el-icon>
      </el-button>
    </el-tooltip>
  </div>

  <!-- 添加模型弹窗 -->
  <el-dialog v-model="showCreate" title="添加模型" width="560px" class="model-dialog">
    <el-form :model="formData" label-width="100px" label-position="left">
      <el-form-item label="厂商">
        <el-select v-model="formData.provider" @change="onProviderChange" style="width: 100%">
          <el-option label="DeepSeek 深度求索" value="deepseek" />
          <el-option label="通义千问 (Qwen)" value="qwen" />
          <el-option label="月之暗面 (Kimi)" value="moonshot" />
          <el-option label="智谱 GLM" value="glm" />
          <el-option label="OpenAI GPT" value="openai" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>

      <el-form-item label="名称">
        <el-input v-model="formData.name" placeholder="如：我的 DeepSeek" />
      </el-form-item>

      <el-form-item label="API Base URL">
        <el-input v-model="formData.base_url" placeholder="https://api.deepseek.com" />
      </el-form-item>

      <el-form-item label="API Key">
        <el-input v-model="formData.api_key" type="password" show-password placeholder="sk-..." />
      </el-form-item>

      <el-form-item label="Chat 模型">
        <el-input v-model="formData.chat_model" placeholder="deepseek-chat" />
      </el-form-item>

      <el-form-item label="推理模型">
        <el-input v-model="formData.reasoner_model" placeholder="deepseek-reasoner (可选)" />
      </el-form-item>

      <el-form-item label="Temperature">
        <el-slider v-model="formData.temperature" :min="0" :max="2" :step="0.1" show-input style="padding-right: 16px" />
      </el-form-item>

      <el-form-item label="Max Tokens">
        <el-input-number v-model="formData.max_tokens" :min="256" :max="32768" :step="512" />
      </el-form-item>

      <el-form-item label="设为默认">
        <el-switch v-model="formData.is_default" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="showCreate = false">取消</el-button>
      <el-button type="primary" @click="submitCreate">添加</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.model-selector {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-bottom: 1px solid var(--ide-border);
  background: var(--ide-bg-elevated);
}

.model-select {
  flex: 1;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-size: 13px;
  color: var(--ide-text);
}

.model-detail {
  font-size: 11px;
  color: var(--ide-text-dim);
  font-family: var(--ide-mono);
}

.add-btn {
  color: var(--ide-text-dim);
}
.add-btn:hover {
  color: var(--ide-accent);
}
</style>
