<script setup>
import { ref, onMounted } from 'vue'
import { fetchMessages, createMessage, updateMessage, deleteMessage } from '@/api/messages'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const messages = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const searchContent = ref('')
const searchUser = ref('')
const searchDateRange = ref([])
let searchTimer = null

const detailVisible = ref(false)
const detailRow = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('新建留言')
const form = ref({ content: '', is_hidden: 0 })
const editingId = ref(null)
const formLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (searchContent.value) params.search = searchContent.value
    if (searchUser.value) params.search = (params.search || '') + ' ' + searchUser.value
    if (searchDateRange.value?.length === 2) {
      params.created_at_after = searchDateRange.value[0].toISOString()
      params.created_at_before = searchDateRange.value[1].toISOString()
    }
    const { data } = await fetchMessages(params)
    messages.value = data.results || data
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
    dialogTitle.value = '编辑留言'
    editingId.value = row.id
    form.value = { content: row.content, is_hidden: row.is_hidden }
  } else {
    dialogTitle.value = '新建留言'
    editingId.value = null
    form.value = { content: '', is_hidden: 0 }
  }
  dialogVisible.value = true
}

async function handleSave() {
  formLoading.value = true
  try {
    if (editingId.value) {
      await updateMessage(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createMessage(form.value)
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
    await ElMessageBox.confirm(`确定删除该留言？`, '确认', { type: 'warning' })
    await deleteMessage(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>留言管理</h2>
      <div class="header-right">
        <el-input
          v-model="searchContent"
          placeholder="搜索留言内容..."
          clearable
          style="width: 200px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-input
          v-model="searchUser"
          placeholder="搜索用户名..."
          clearable
          style="width: 160px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-date-picker
          v-model="searchDateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DD HH:mm"
          style="width: 320px"
          @change="load"
        />
        <el-button type="primary" @click="openDialog()">新建留言</el-button>
      </div>
    </div>

    <el-table :data="messages" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="content" label="留言内容" min-width="240" show-overflow-tooltip />
      <el-table-column prop="user_name" label="用户" min-width="100">
        <template #default="{ row }">
          <span :style="{ color: row.user_name ? 'var(--color-text)' : 'var(--color-text-secondary)' }">
            {{ row.user_name || '游客' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="like_count" label="点赞数" min-width="80" align="center" />
      <el-table-column label="隐藏" min-width="80" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_hidden === 1"
            @change="(val) => updateMessage(row.id, { is_hidden: val ? 1 : 0 }).then(() => load())"
          />
        </template>
      </el-table-column>
      <el-table-column label="留言时间" min-width="160">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
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

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" title="留言详情" width="500px" destroy-on-close>
      <el-descriptions v-if="detailRow" :column="1" border>
        <el-descriptions-item label="ID">{{ detailRow.id }}</el-descriptions-item>
        <el-descriptions-item label="用户">{{ detailRow.user_name || '游客' }}</el-descriptions-item>
        <el-descriptions-item label="内容">{{ detailRow.content }}</el-descriptions-item>
        <el-descriptions-item label="点赞数">{{ detailRow.like_count }}</el-descriptions-item>
        <el-descriptions-item label="隐藏">
          <el-tag :type="detailRow.is_hidden ? 'danger' : 'success'" size="small">
            {{ detailRow.is_hidden ? '已隐藏' : '显示中' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="留言时间">{{ formatDate(detailRow.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- Edit dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form :model="form" label-width="70px">
        <el-form-item label="留言内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="3"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="是否隐藏">
          <el-switch
            :model-value="form.is_hidden === 1"
            @change="(val) => form.is_hidden = val ? 1 : 0"
          />
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
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 16px; flex-wrap: wrap; }
.page-header h2 { font-size: 1.3rem; white-space: nowrap; }
.header-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

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
