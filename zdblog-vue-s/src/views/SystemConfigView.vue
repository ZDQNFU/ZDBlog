<script setup>
import { ref, onMounted } from 'vue'
import { fetchConfigs, createConfig, updateConfig, deleteConfig } from '@/api/systemConfig'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const configs = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const searchKey = ref('')
let searchTimer = null

const detailVisible = ref(false)
const detailRow = ref(null)

const dialogVisible = ref(false)
const dialogTitle = ref('新建配置')
const form = ref({ key: '', value: '', value_type: 'string', description: '', is_encrypted: false })
const editingId = ref(null)
const formLoading = ref(false)

const valueTypes = [
  { label: 'string', value: 'string' },
  { label: 'int', value: 'int' },
  { label: 'bool', value: 'bool' },
  { label: 'json', value: 'json' },
]

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (searchKey.value) params.search = searchKey.value
    const { data } = await fetchConfigs(params)
    configs.value = data.results || data
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
    dialogTitle.value = '编辑配置'
    editingId.value = row.id
    form.value = {
      key: row.key,
      value: row.value || '',
      value_type: row.value_type || 'string',
      description: row.description || '',
      is_encrypted: row.is_encrypted || false,
    }
  } else {
    dialogTitle.value = '新建配置'
    editingId.value = null
    form.value = { key: '', value: '', value_type: 'string', description: '', is_encrypted: false }
  }
  dialogVisible.value = true
}

async function handleSave() {
  formLoading.value = true
  try {
    if (editingId.value) {
      await updateConfig(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createConfig(form.value)
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
    await ElMessageBox.confirm(`确定删除配置 "${row.key}"？`, '确认', { type: 'warning' })
    await deleteConfig(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

function valueTypeTag(type) {
  const map = { string: 'info', int: 'warning', bool: 'success', json: '' }
  return map[type] || 'info'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>系统设置</h2>
      <div class="header-right">
        <el-input
          v-model="searchKey"
          placeholder="搜索配置键名..."
          clearable
          style="width: 220px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-button type="primary" @click="openDialog()">新建配置</el-button>
      </div>
    </div>

    <el-table :data="configs" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="key" label="键名" min-width="160" show-overflow-tooltip />
      <el-table-column label="值" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.is_encrypted" style="color: var(--color-text-secondary);">***</span>
          <span v-else>{{ row.value }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="value_type" label="类型" min-width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="valueTypeTag(row.value_type)" size="small">{{ row.value_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="加密" min-width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_encrypted ? 'danger' : 'success'" size="small">
            {{ row.is_encrypted ? '加密' : '明文' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" min-width="160">
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

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" title="配置详情" width="550px" destroy-on-close>
      <el-descriptions v-if="detailRow" :column="1" border>
        <el-descriptions-item label="ID">{{ detailRow.id }}</el-descriptions-item>
        <el-descriptions-item label="键名">{{ detailRow.key }}</el-descriptions-item>
        <el-descriptions-item label="值">
          <span v-if="detailRow.is_encrypted">***</span>
          <span v-else>{{ detailRow.value }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="值类型">
          <el-tag :type="valueTypeTag(detailRow.value_type)" size="small">{{ detailRow.value_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="说明">{{ detailRow.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="加密存储">
          <el-tag :type="detailRow.is_encrypted ? 'danger' : 'success'" size="small">
            {{ detailRow.is_encrypted ? '是' : '否' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(detailRow.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(detailRow.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- Edit dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="550px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item label="键名">
          <el-input v-model="form.key" placeholder="GITHUB_TOKEN" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="值">
          <el-input
            v-model="form.value"
            type="textarea"
            :rows="3"
            placeholder="配置值"
          />
        </el-form-item>
        <el-form-item label="值类型">
          <el-select v-model="form.value_type">
            <el-option v-for="t in valueTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="配置说明（可选）" />
        </el-form-item>
        <el-form-item label="加密存储">
          <el-switch v-model="form.is_encrypted" />
          <span style="margin-left: 8px; font-size: 0.85rem; color: var(--color-text-secondary);">
            开启后值将加密存入数据库
          </span>
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
