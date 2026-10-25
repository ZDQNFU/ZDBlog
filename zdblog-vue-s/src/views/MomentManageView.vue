<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchMoments, createMoment, updateMoment, deleteMoment } from '@/api/moments'

const moments = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const publishedFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const changingId = ref(null)
const form = ref({ content: '', is_published: true })
let searchTimer, requestId = 0

function showError(error, fallback) {
  const data = error.response?.data
  ElMessage.error(data?.detail || Object.values(data || {}).flat().join('；') || fallback)
}

async function load() {
  const id = ++requestId
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value.trim()) params.search = search.value.trim()
    if (publishedFilter.value !== '') params.is_published = publishedFilter.value
    const { data } = await fetchMoments(params)
    if (id !== requestId) return
    moments.value = data.results
    total.value = data.count
  } catch (e) {
    if (id !== requestId) return
    if (e.response?.status === 404 && page.value > 1) {
      page.value -= 1
      await load()
    } else showError(e, '动态加载失败')
  } finally {
    if (id === requestId) loading.value = false
  }
}

function filterChanged() { page.value = 1; load() }
function searchChanged() { clearTimeout(searchTimer); searchTimer = setTimeout(filterChanged, 300) }
function openEditor(row) {
  editingId.value = row?.id || null
  form.value = { content: row?.content || '', is_published: row?.is_published ?? true }
  dialogVisible.value = true
}

async function save() {
  if (saving.value) return
  const content = form.value.content.trim()
  if (!content) { ElMessage.warning('请输入动态内容'); return }
  saving.value = true
  try {
    const data = { content, is_published: form.value.is_published }
    if (editingId.value) await updateMoment(editingId.value, data)
    else await createMoment(data)
    ElMessage.success(data.is_published ? '动态已发布' : '动态已保存为隐藏状态')
    dialogVisible.value = false
    if (!editingId.value) page.value = 1
    await load()
  } catch (e) { showError(e, '保存失败') }
  finally { saving.value = false }
}

async function setPublished(row, value) {
  if (changingId.value) return
  changingId.value = row.id
  try {
    await updateMoment(row.id, { is_published: value })
    ElMessage.success(value ? '动态已公开' : '动态已隐藏')
    await load()
  } catch (e) { showError(e, '状态更新失败') }
  finally { changingId.value = null }
}

async function remove(row) {
  try { await ElMessageBox.confirm('删除这条动态及其点赞记录？此操作无法撤销。', '删除动态', { type: 'warning' }) }
  catch { return }
  try {
    await deleteMoment(row.id)
    ElMessage.success('动态已删除')
    await load()
  } catch (e) { showError(e, '删除失败') }
}

function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN') : '-' }
onMounted(load)
onUnmounted(() => { clearTimeout(searchTimer); requestId += 1 })
</script>

<template>
  <div>
    <header class="page-header">
      <div><h2>动态管理</h2><p>记录短文字，分享最近的想法与生活。</p></div>
      <div class="header-actions">
        <el-input v-model="search" clearable placeholder="搜索动态内容或发布人" aria-label="搜索动态" @input="searchChanged" />
        <el-select v-model="publishedFilter" placeholder="全部状态" aria-label="显示状态" @change="filterChanged"><el-option label="全部状态" value="" /><el-option label="公开" value="true" /><el-option label="隐藏" value="false" /></el-select>
        <el-button type="primary" @click="openEditor()">发布动态</el-button>
      </div>
    </header>
    <el-table :data="moments" v-loading="loading" stripe border empty-text="暂无动态，发布第一条吧">
      <el-table-column prop="content" label="动态内容" min-width="320" show-overflow-tooltip><template #default="{ row }"><p class="content-preview">{{ row.content }}</p></template></el-table-column>
      <el-table-column prop="author_name" label="发布人" width="120" />
      <el-table-column prop="like_count" label="点赞数" width="90" align="center" />
      <el-table-column label="公开显示" width="110" align="center"><template #default="{ row }"><el-switch :model-value="row.is_published" :disabled="changingId !== null" :loading="changingId === row.id" :aria-label="`设置动态公开状态`" @change="value => setPublished(row, value)" /></template></el-table-column>
      <el-table-column label="发布时间" min-width="175"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="150"><template #default="{ row }"><el-button size="small" @click="openEditor(row)">编辑</el-button><el-button size="small" type="danger" @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-if="total" class="pagination" background layout="total, sizes, prev, pager, next" :total="total" :page-size="pageSize" :current-page="page" :page-sizes="[10, 20, 50]" @current-change="value => { page = value; load() }" @size-change="value => { pageSize = value; filterChanged() }" />
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑动态' : '发布动态'" width="min(560px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving">
      <el-form :model="form" label-position="top" :disabled="saving" @submit.prevent="save">
        <el-form-item label="动态内容"><el-input v-model="form.content" type="textarea" :rows="7" maxlength="500" show-word-limit placeholder="写下此刻的想法…" aria-label="动态内容" /></el-form-item>
        <el-form-item><el-switch v-model="form.is_published" active-text="公开显示" inactive-text="隐藏" /></el-form-item>
      </el-form>
      <template #footer><el-button :disabled="saving" @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">{{ editingId ? '保存修改' : (form.is_published ? '发布动态' : '保存动态') }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px; margin-bottom: 24px; }
.page-header h2 { font-size: 1.3rem; }
.page-header p { margin-top: 6px; font-size: .82rem; color: var(--color-text-secondary); }
.header-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.header-actions .el-input { width: 240px; }
.header-actions .el-select { width: 120px; }
.content-preview { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pagination { margin-top: 20px; justify-content: center; }
</style>
