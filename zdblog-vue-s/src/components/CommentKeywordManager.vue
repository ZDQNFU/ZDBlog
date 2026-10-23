<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import {
  fetchCommentKeywords, createCommentKeyword, updateCommentKeyword, deleteCommentKeyword,
} from '@/api/comments'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const keywords = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const search = ref('')
const actionFilter = ref('')
const editingVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const busyId = ref(null)
const form = ref({ word: '', action: 'reject', enabled: true, description: '' })

function showError(error, fallback) {
  const data = error.response?.data
  ElMessage.error(data?.detail || Object.values(data || {}).flat().join('；') || fallback)
}

async function load() {
  loading.value = true
  try {
    const { data } = await fetchCommentKeywords({
      page: page.value, page_size: 20, search: search.value, action: actionFilter.value,
    })
    keywords.value = data.results
    total.value = data.count
  } catch (error) {
    if (error.response?.status === 404 && page.value > 1) {
      page.value -= 1
      await load()
      return
    }
    showError(error, '关键词加载失败')
  } finally {
    loading.value = false
  }
}

function applyFilter() { page.value = 1; load() }
function changePage(value) { page.value = value; load() }

function openEditor(row = null) {
  editingId.value = row?.id ?? null
  form.value = row
    ? { word: row.word, action: row.action, enabled: row.enabled, description: row.description }
    : { word: '', action: 'reject', enabled: true, description: '' }
  editingVisible.value = true
}

async function save() {
  if (saving.value) return
  if (!form.value.word.trim()) {
    ElMessage.warning('请填写关键词')
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value, word: form.value.word.trim() }
    if (editingId.value === null) {
      await createCommentKeyword(payload)
      page.value = 1
    } else {
      await updateCommentKeyword(editingId.value, payload)
    }
    ElMessage.success('关键词已保存，立即生效')
    editingVisible.value = false
    await load()
  } catch (error) {
    showError(error, '关键词保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleKeyword(row, enabled) {
  busyId.value = row.id
  try {
    await updateCommentKeyword(row.id, { enabled })
    row.enabled = enabled
    ElMessage.success(enabled ? '关键词已启用' : '关键词已停用')
  } catch (error) {
    showError(error, '更新失败')
  } finally {
    busyId.value = null
  }
}

async function removeKeyword(row) {
  try {
    await ElMessageBox.confirm(`确定删除关键词“${row.word}”？`, '删除关键词', { type: 'warning' })
    busyId.value = row.id
    await deleteCommentKeyword(row.id)
    ElMessage.success('关键词已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') showError(error, '删除失败')
  } finally {
    busyId.value = null
  }
}

function closeEditor(done) { if (!saving.value) done() }

watch(() => props.modelValue, (visible) => {
  if (visible) load()
}, { immediate: true })
</script>

<template>
  <el-dialog
    :model-value="modelValue" title="审核关键词" width="min(1000px, 94vw)"
    @update:model-value="emit('update:modelValue', $event)" @closed="editingVisible = false"
  >
    <p class="keyword-intro">内置词和自定义词统一在这里维护。启用的关键词对新提交的评论生效，内置词也可以修改或停用。</p>
    <div class="keyword-toolbar">
      <div class="keyword-search">
        <el-input v-model="search" placeholder="搜索关键词或备注" clearable :prefix-icon="Search"
          @keyup.enter="applyFilter" @clear="applyFilter" />
        <el-select v-model="actionFilter" placeholder="全部处理方式" clearable @change="applyFilter">
          <el-option label="直接拒绝" value="reject" />
          <el-option label="进入待审" value="review" />
        </el-select>
        <el-button @click="applyFilter">查询</el-button>
      </div>
      <el-button type="primary" :icon="Plus" @click="openEditor()">添加关键词</el-button>
    </div>

    <el-table :data="keywords" v-loading="loading" border stripe empty-text="暂无符合条件的关键词">
      <el-table-column prop="word" label="关键词" min-width="160" show-overflow-tooltip />
      <el-table-column label="处理方式" width="110">
        <template #default="{ row }">
          <el-tag :type="row.action === 'reject' ? 'danger' : 'warning'">{{ row.action === 'reject' ? '直接拒绝' : '进入待审' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="90">
        <template #default="{ row }">{{ row.source === 'builtin' ? '内置' : '自定义' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="分类 / 备注" min-width="180" show-overflow-tooltip />
      <el-table-column label="启用" width="85" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" :loading="busyId === row.id" :disabled="busyId !== null"
            :aria-label="`${row.enabled ? '停用' : '启用'}关键词${row.word}`" @change="toggleKeyword(row, $event)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :disabled="busyId !== null" @click="openEditor(row)">编辑</el-button>
          <el-button size="small" type="danger" :disabled="busyId !== null" @click="removeKeyword(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="keyword-pagination">
      <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="20"
        :current-page="page" @current-change="changePage" />
    </div>
  </el-dialog>

  <el-dialog v-model="editingVisible" :title="editingId === null ? '添加关键词' : '编辑关键词'"
    width="min(480px, 94vw)" append-to-body :close-on-click-modal="false" :before-close="closeEditor">
    <el-form :model="form" label-position="top" :disabled="saving">
      <el-form-item label="关键词" required>
        <el-input v-model="form.word" maxlength="100" show-word-limit placeholder="填写需要过滤的词或短语" />
      </el-form-item>
      <el-form-item label="命中后如何处理">
        <el-radio-group v-model="form.action">
          <el-radio value="reject">直接拒绝</el-radio>
          <el-radio value="review">进入待审</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="分类 / 备注">
        <el-input v-model="form.description" maxlength="200" placeholder="例如：辱骂、广告或需要人工判断的内容" />
      </el-form-item>
      <el-form-item label="启用"><el-switch v-model="form.enabled" aria-label="启用该关键词" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="saving" @click="editingVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.keyword-intro { margin: 0 0 20px; color: var(--el-text-color-secondary); line-height: 1.7; }
.keyword-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.keyword-search { display: flex; gap: 10px; flex-wrap: wrap; }
.keyword-search .el-input { width: 230px; }
.keyword-search .el-select { width: 150px; }
.keyword-pagination { display: flex; justify-content: center; margin-top: 20px; overflow-x: auto; }
@media (max-width: 600px) {
  .keyword-search { width: 100%; }
  .keyword-search .el-input { flex: 1 1 100%; width: 100%; }
  .keyword-search .el-select { flex: 1; }
}
</style>
