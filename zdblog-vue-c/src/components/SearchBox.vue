<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'search'])

const inputVal = ref(props.modelValue)
let timer = null

function emitSearch() {
  emit('search', inputVal.value)
}

function onInput(e) {
  inputVal.value = e.target.value
  emit('update:modelValue', inputVal.value)
  clearTimeout(timer)
  timer = setTimeout(emitSearch, 300)
}

function onKeydown(e) {
  if (e.key === 'Enter') {
    clearTimeout(timer)
    emitSearch()
  }
}

function onClear() {
  inputVal.value = ''
  emit('update:modelValue', '')
  clearTimeout(timer)
  emitSearch()
}

watch(() => props.modelValue, (val) => {
  if (val !== inputVal.value) {
    inputVal.value = val
  }
})

onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <div class="search-box">
    <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
    <input
      :value="inputVal"
      type="search"
      class="search-input"
      placeholder="搜索文章..."
      aria-label="搜索文章"
      @input="onInput"
      @keydown="onKeydown"
    />
    <button v-if="inputVal" class="search-clear" @click="onClear" aria-label="清除搜索">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.search-box {
  position: relative;
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--color-text-secondary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 13px 38px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-input::placeholder {
  color: var(--color-text-secondary);
}
.search-input::-webkit-search-cancel-button { -webkit-appearance: none; }
.search-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.search-clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.search-clear:hover {
  background: var(--color-border);
  color: var(--color-text);
}
</style>
