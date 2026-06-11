<script setup>
import { ref, onMounted } from 'vue'
import { fetchUsers, createUser, updateUser, deleteUser } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const users = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const search = ref('')
const filterSuperuser = ref('')
const filterActive = ref('')
let searchTimer = null

const detailVisible = ref(false)
const detailRow = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('新建用户')
const form = ref({ username: '', email: '', password: '', is_superuser: false, is_staff: false, is_active: true })
const editingId = ref(null)
const formLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (filterSuperuser.value !== '') params.is_superuser = filterSuperuser.value
    if (filterActive.value !== '') params.is_active = filterActive.value
    const { data } = await fetchUsers(params)
    users.value = data.results
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

function onFilterChange() {
  page.value = 1
  load()
}

function openDialog(row) {
  if (row) {
    dialogTitle.value = '编辑用户'
    editingId.value = row.id
    form.value = {
      username: row.username,
      email: row.email || '',
      password: '',
      is_superuser: row.is_superuser,
      is_staff: row.is_staff,
      is_active: row.is_active,
    }
  } else {
    dialogTitle.value = '新建用户'
    editingId.value = null
    form.value = { username: '', email: '', password: '', is_superuser: false, is_staff: false, is_active: true }
  }
  dialogVisible.value = true
}

async function handleSave() {
  formLoading.value = true
  try {
    const payload = { ...form.value }
    if (!payload.password) delete payload.password
    if (editingId.value) {
      await updateUser(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createUser(payload)
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
    await ElMessageBox.confirm(`确定删除用户「${row.username}」？`, '确认', { type: 'warning' })
    await deleteUser(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function onPageChange(p) { page.value = p; load() }
function onSizeChange(s) { pageSize.value = s; page.value = 1; load() }

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>用户管理</h2>
      <div class="header-right">
        <el-input
          v-model="search"
          placeholder="搜索用户名或邮箱..."
          clearable
          style="width: 220px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-select v-model="filterSuperuser" placeholder="超级管理" clearable style="width: 120px" @change="onFilterChange">
          <el-option label="是" :value="true" />
          <el-option label="否" :value="false" />
        </el-select>
        <el-select v-model="filterActive" placeholder="激活状态" clearable style="width: 120px" @change="onFilterChange">
          <el-option label="激活" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
        <el-button type="primary" @click="openDialog()">新建用户</el-button>
      </div>
    </div>

    <el-table :data="users" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column label="超级管理" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_superuser ? 'danger' : 'info'" size="small">{{ row.is_superuser ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="员工" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_staff ? 'warning' : 'info'" size="small">{{ row.is_staff ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="激活" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" min-width="120">
        <template #default="{ row }">{{ formatDate(row.date_joined) }}</template>
      </el-table-column>
      <el-table-column label="最后登录" min-width="120">
        <template #default="{ row }">{{ formatDate(row.last_login) }}</template>
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

    <el-dialog v-model="detailVisible" title="用户详情" width="500px" destroy-on-close>
      <el-descriptions v-if="detailRow" :column="2" border>
        <el-descriptions-item label="用户名">{{ detailRow.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ detailRow.email || '-' }}</el-descriptions-item>
        <el-descriptions-item label="超级管理">
          <el-tag :type="detailRow.is_superuser ? 'danger' : 'info'" size="small">{{ detailRow.is_superuser ? '是' : '否' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="员工">
          <el-tag :type="detailRow.is_staff ? 'warning' : 'info'" size="small">{{ detailRow.is_staff ? '是' : '否' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="激活">
          <el-tag :type="detailRow.is_active ? 'success' : 'danger'" size="small">{{ detailRow.is_active ? '是' : '否' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ formatDate(detailRow.date_joined) }}</el-descriptions-item>
        <el-descriptions-item label="最后登录" :span="2">{{ formatDate(detailRow.last_login) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item :label="editingId ? '新密码(留空不改)' : '密码'">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="超级管理">
          <el-switch v-model="form.is_superuser" />
        </el-form-item>
        <el-form-item label="员工">
          <el-switch v-model="form.is_staff" />
        </el-form-item>
        <el-form-item label="激活">
          <el-switch v-model="form.is_active" />
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
