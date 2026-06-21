<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import type { AgentConfigCreate } from '@/api'

const store = useAppStore()

const showCreate = ref(false)
const formData = ref<AgentConfigCreate>({
  name: '',
  description: '',
  avatar: '🤖',
  system_prompt: '',
  temperature: 0.3,
  model_route: 'chat',
  tools: ['rag_search'],
})

const avatarOptions = ['🤖', '💻', '🏗️', '🔍', '📝', '🚀', '🐛', '⚡', '🎨', '📊', '🔧', '🧪']

function selectAgent(id: string) {
  store.currentAgentId = id
}

function openCreate() {
  formData.value = {
    name: '',
    description: '',
    avatar: '🤖',
    system_prompt: '',
    temperature: 0.3,
    model_route: 'chat',
    tools: ['rag_search'],
  }
  showCreate.value = true
}

async function submitCreate() {
  if (!formData.value.name || !formData.value.system_prompt) return
  await store.createAgent(formData.value)
  showCreate.value = false
}

async function removeAgent(id: string, isBuiltin: boolean) {
  if (isBuiltin) return
  await store.deleteAgent(id)
}
</script>

<template>
  <!-- 智能体选择器 -->
  <div class="agent-selector">
    <el-select
      :model-value="store.currentAgentId"
      size="small"
      class="agent-select"
      @change="selectAgent"
    >
      <template #prefix>
        <span class="agent-avatar">{{ store.currentAgent?.avatar || '🤖' }}</span>
      </template>
      <el-option
        v-for="agent in store.agents"
        :key="agent.id"
        :value="agent.id"
        :label="agent.name"
      >
        <div class="agent-option">
          <span class="agent-option-avatar">{{ agent.avatar }}</span>
          <div class="agent-option-info">
            <span class="agent-option-name">{{ agent.name }}</span>
            <span class="agent-option-desc">{{ agent.description }}</span>
          </div>
          <el-tag v-if="agent.is_builtin" size="small" type="info">内置</el-tag>
        </div>
      </el-option>
    </el-select>

    <el-tooltip content="创建智能体" placement="bottom">
      <el-button text size="small" class="create-btn" @click="openCreate">
        <el-icon><Plus /></el-icon>
      </el-button>
    </el-tooltip>
  </div>

  <!-- 创建智能体弹窗 -->
  <el-dialog v-model="showCreate" title="创建智能体" width="500px" class="agent-dialog">
    <el-form :model="formData" label-width="80px" label-position="left">
      <el-form-item label="头像">
        <div class="avatar-picker">
          <button
            v-for="emoji in avatarOptions"
            :key="emoji"
            class="avatar-btn"
            :class="{ active: formData.avatar === emoji }"
            @click="formData.avatar = emoji"
          >
            {{ emoji }}
          </button>
        </div>
      </el-form-item>

      <el-form-item label="名称">
        <el-input v-model="formData.name" placeholder="如：Python 专家" />
      </el-form-item>

      <el-form-item label="描述">
        <el-input v-model="formData.description" placeholder="智能体简介" />
      </el-form-item>

      <el-form-item label="System Prompt">
        <el-input
          v-model="formData.system_prompt"
          type="textarea"
          :rows="4"
          placeholder="定义这个智能体的角色和行为..."
        />
      </el-form-item>

      <el-form-item label="模型">
        <el-radio-group v-model="formData.model_route">
          <el-radio value="chat">Chat (快速)</el-radio>
          <el-radio value="reasoner">Reasoner (深度思考)</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="温度">
        <el-slider v-model="formData.temperature" :min="0" :max="2" :step="0.1" show-input style="padding-right: 16px" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="showCreate = false">取消</el-button>
      <el-button type="primary" @click="submitCreate">创建</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.agent-selector {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--ide-border);
  background: var(--ide-bg-elevated);
}

.agent-select {
  flex: 1;
}

.agent-avatar {
  font-size: 16px;
}

.agent-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.agent-option-avatar {
  font-size: 20px;
}

.agent-option-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.agent-option-name {
  font-size: 13px;
  color: var(--ide-text);
}

.agent-option-desc {
  font-size: 11px;
  color: var(--ide-text-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.create-btn {
  color: var(--ide-text-dim);
}
.create-btn:hover {
  color: var(--ide-accent);
}

.avatar-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.avatar-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--ide-border);
  border-radius: 6px;
  background: var(--ide-bg);
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.avatar-btn:hover {
  border-color: var(--ide-accent);
}

.avatar-btn.active {
  border-color: var(--ide-accent);
  background: var(--ide-bg-active);
  box-shadow: 0 0 0 2px var(--ide-accent);
}
</style>
