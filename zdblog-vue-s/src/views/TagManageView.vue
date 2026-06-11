<script setup>
import { ref, onMounted } from 'vue'
import { fetchTags, createTag, updateTag, deleteTag } from '@/api/tags'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const tags = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
let searchTimer = null

const detailVisible = ref(false)
const detailRow = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('新建标签')
const form = ref({ name: '', color: '#3b82f6' })
const editingId = ref(null)
const formLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const { data } = await fetchTags(params)
    tags.value = data.results || data
    total.value = data.count || 0
  } finally {
    loading.value = false
  }
}

function onSearchChange() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 300)
}

function onPageChange(p) {
  page.value = p
  load()
}

function onSizeChange(s) {
  pageSize.value = s
  page.value = 1
  load()
}

function openDialog(row) {
  if (row) {
    dialogTitle.value = '编辑标签'
    editingId.value = row.id
    form.value = { name: row.name, color: row.color }
  } else {
    dialogTitle.value = '新建标签'
    editingId.value = null
    form.value = { name: '', color: '#3b82f6' }
  }
  dialogVisible.value = true
}

async function handleSave() {
  formLoading.value = true
  try {
    if (editingId.value) {
      await updateTag(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createTag(form.value)
      ElMessage.success('创建成功')
    }
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
    await ElMessageBox.confirm(`确定删除标签「${row.name}」？`, '确认', { type: 'warning' })
    await deleteTag(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>标签管理</h2>
      <div class="header-right">
        <el-input
          v-model="search"
          placeholder="搜索标签名称..."
          clearable
          style="width: 240px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-button type="primary" @click="openDialog()">新建标签</el-button>
      </div>
    </div>

    <el-table :data="tags" v-loading="loading" stripe border style="width:100%">
      <el-table-column label="预览" min-width="80">
        <template #default="{ row }">
          <el-tag :color="row.color" size="small" style="color:#fff">{{ row.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="color" label="颜色" min-width="90" />
      <el-table-column label="创建时间" min-width="110">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="最后修改" min-width="110">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button size="small" class="detail-btn" @click="detailRow = row; detailVisible = true">详情</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 0"
      style="margin-top:16px;justify-content:center"
      background
      layout="total, sizes, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      :page-sizes="[10, 20, 50]"
      @current-change="onPageChange"
      @size-change="onSizeChange"
    />

    <el-dialog v-model="detailVisible" title="标签详情" width="460px" destroy-on-close>
      <el-descriptions v-if="detailRow" :column="1" border>
        <el-descriptions-item label="名称">{{ detailRow.name }}</el-descriptions-item>
        <el-descriptions-item label="颜色">
          <div style="display:flex;align-items:center;gap:8px;">
            <span :style="{ display:'inline-block',width:20,height:20,borderRadius:4,background:detailRow.color }"></span>
            {{ detailRow.color }}
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(detailRow.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后修改">{{ formatDate(detailRow.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="460px" destroy-on-close>
      <el-form :model="form" label-width="60px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color" />
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
.header-right { display: flex; align-items: center; gap: 12px; }

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
