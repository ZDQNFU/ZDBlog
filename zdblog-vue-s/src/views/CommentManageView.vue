<script setup>
import { ref, onMounted } from 'vue'
import { fetchComments, updateComment, deleteComment } from '@/api/comments'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const comments = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const search = ref('')
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
    const { data } = await fetchComments(params)
    comments.value = data.results
    total.value = data.count
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
    ElMessage.success('更新成功')
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
      <el-input
        v-model="search"
        placeholder="搜索评论者或内容..."
        clearable
        style="width: 280px"
        :prefix-icon="Search"
        @input="onSearchChange"
        @clear="load"
      />
    </div>

    <el-table :data="comments" v-loading="loading" stripe border style="width:100%">
      <el-table-column label="文章" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.article_title || '-' }}</template>
      </el-table-column>
      <el-table-column prop="author_name" label="作者" width="120" />
      <el-table-column label="内容" min-width="300" show-overflow-tooltip>
        <template #default="{ row }">{{ truncate(row.content) }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="120">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="最后修改" width="120">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
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
        <el-descriptions-item label="创建时间">{{ formatDate(detailRow.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后修改">{{ formatDate(detailRow.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form :model="form" label-width="60px">
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="5" />
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
