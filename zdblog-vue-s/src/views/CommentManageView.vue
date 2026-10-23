<script setup>
import { ref, onMounted } from 'vue'
import { fetchComments, updateComment, deleteComment } from '@/api/comments'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import CommentKeywordManager from '@/components/CommentKeywordManager.vue'

const comments = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const search = ref('')
const statusFilter = ref('')
const reviewingId = ref(null)
const keywordDialogVisible = ref(false)
const statusOptions = [
  { value: 'pending', label: '待审核', type: 'warning' },
  { value: 'approved', label: '已通过', type: 'success' },
  { value: 'rejected', label: '已拒绝', type: 'danger' },
]
let searchTimer = null

const detailVisible = ref(false)
const detailRow = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('编辑评论')
const form = ref({ content: '' })
const editingId = ref(null)
const formLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await fetchComments(params)
    comments.value = data.results
    total.value = data.count
    if (!comments.value.length && page.value > 1) {
      page.value = Math.max(1, Math.ceil(total.value / pageSize.value))
      await load()
    }
  } catch (error) {
    if (error.response?.status === 404 && page.value > 1) {
      page.value -= 1
      await load()
      return
    }
    ElMessage.error('评论列表加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function onSearchChange() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
}

function openDialog(row) {
  dialogTitle.value = '编辑评论'
  editingId.value = row.id
  form.value = { content: row.content }
  dialogVisible.value = true
}

async function handleSave() {
  formLoading.value = true
  try {
    await updateComment(editingId.value, form.value)
    ElMessage.success('已保存并重新自动审核')
    dialogVisible.value = false
    load()
  } catch (e) {
    const detail = e.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : Object.values(e.response?.data || {}).flat().join(', ')
    ElMessage.error(msg || '操作失败')
  } finally {
    formLoading.value = false
  }
}

async function handleReview(row, status) {
  reviewingId.value = row.id
  try {
    await updateComment(row.id, { status })
    ElMessage.success(status === 'approved' ? '已通过审核' : '已拒绝该评论')
    await load()
  } catch {
    ElMessage.error('审核失败，请稍后重试')
  } finally {
    reviewingId.value = null
  }
}

function onStatusChange() { page.value = 1; load() }
function statusInfo(value) { return statusOptions.find(option => option.value === value) || statusOptions[0] }

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除该评论？`, '确认', { type: 'warning' })
    await deleteComment(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function onPageChange(p) { page.value = p; load() }
function onSizeChange(s) { pageSize.value = s; page.value = 1; load() }

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }

function truncate(str, len = 60) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>评论管理</h2>
      <div class="filters">
        <el-select v-model="statusFilter" placeholder="全部审核状态" clearable style="width: 160px" @change="onStatusChange">
          <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-input
          v-model="search"
          placeholder="搜索评论者或内容..."
          clearable
          style="width: 280px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-button type="primary" @click="keywordDialogVisible = true">审核关键词</el-button>
      </div>
    </div>

    <el-alert class="moderation-hint" type="info" :closable="false" show-icon
      title="待审核和已拒绝的评论不会公开；与已拒绝评论相同的内容再次提交将直接拒绝。可在“审核关键词”中管理过滤词。" />

    <CommentKeywordManager v-model="keywordDialogVisible" />

    <el-table :data="comments" v-loading="loading" stripe border style="width:100%">
      <el-table-column label="文章" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.article_title || '-' }}</template>
      </el-table-column>
      <el-table-column prop="author_name" label="作者" width="120" />
      <el-table-column label="内容" min-width="300" show-overflow-tooltip>
        <template #default="{ row }">{{ truncate(row.content) }}</template>
      </el-table-column>
      <el-table-column label="审核状态" width="110">
        <template #default="{ row }"><el-tag :type="statusInfo(row.status).type">{{ statusInfo(row.status).label }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="moderation_reason" label="自动审核说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="创建时间" width="120">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="最后修改" width="120">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="350" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'approved'" size="small" type="success" :disabled="reviewingId !== null" @click="handleReview(row, 'approved')">通过</el-button>
          <el-button v-if="row.status !== 'rejected'" size="small" type="warning" :disabled="reviewingId !== null" @click="handleReview(row, 'rejected')">拒绝</el-button>
          <el-button size="small" type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button size="small" class="detail-btn" @click="detailRow = row; detailVisible = true">详情</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        background layout="total, sizes, prev, pager, next"
        :total="total" :page-size="pageSize" :current-page="page"
        :page-sizes="[10, 20, 50]"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>

    <el-dialog v-model="detailVisible" title="评论详情" width="500px" destroy-on-close>
      <el-descriptions v-if="detailRow" :column="1" border>
        <el-descriptions-item label="文章">{{ detailRow.article_title || '-' }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ detailRow.author_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="内容">{{ detailRow.content }}</el-descriptions-item>
        <el-descriptions-item label="审核状态">{{ statusInfo(detailRow.status).label }}</el-descriptions-item>
        <el-descriptions-item label="自动审核说明">{{ detailRow.moderation_reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="人工审核人">{{ detailRow.reviewed_by_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="人工审核时间">{{ detailRow.reviewed_at ? new Date(detailRow.reviewed_at).toLocaleString('zh-CN') : '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(detailRow.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后修改">{{ formatDate(detailRow.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form :model="form" label-width="60px">
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="5" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 16px; }
.page-header h2 { font-size: 1.3rem; white-space: nowrap; }
.filters { display: flex; gap: 12px; flex-wrap: wrap; }
.moderation-hint { margin-bottom: 16px; }
@media (max-width: 768px) { .page-header { align-items: flex-start; flex-direction: column; } }
.pagination-wrap { margin-top: 20px; display: flex; justify-content: center; }

.detail-btn {
  --el-button-bg-color: #e7a642;
  --el-button-border-color: #e7a642;
  --el-button-text-color: #fff;
}
.detail-btn:hover {
  --el-button-bg-color: #d4952e;
  --el-button-border-color: #d4952e;
  --el-button-text-color: #fff;
}
</style>
