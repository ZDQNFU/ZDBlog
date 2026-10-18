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
const helpVisible = ref(false)

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

const helpItems = [
  {
    key: 'ICP_BEIAN',
    title: 'ICP 备案号',
    description: '显示在前台页脚，并链接到工信部备案查询。留空则页脚不显示该项。',
    example: '皖ICP备2024030355号',
  },
  {
    key: 'GONGAN_BEIAN',
    title: '公安备案号',
    description: '显示在前台页脚，并链接到全国互联网安全管理服务平台。留空则页脚不显示该项。',
    example: '皖公网安备34180002000000号',
  },
  {
    key: 'GITHUB_TOKEN',
    title: 'GitHub 访问令牌',
    description: '用于把文章图片上传到 GitHub。请填写对目标仓库有写入权限的 Personal Access Token，并开启“加密存储”。',
    example: 'GitHub 生成的访问令牌',
  },
  {
    key: 'GITHUB_ARTICLE_PATH',
    title: '文章图片仓库目录',
    description: '填写图片上传目标仓库的目录地址，需要包含 owner、仓库名、分支和目录。',
    example: 'https://github.com/owner/repo/tree/main/article',
  },
  {
    key: 'GITHUB_USER_PATH',
    title: 'GitHub 用户路径',
    description: '该配置目前只登记在数据库中，现有代码没有读取它；修改后暂不会影响功能。',
    example: '当前未使用',
  },
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
        <el-button @click="helpVisible = true">
          <el-icon><QuestionFilled /></el-icon>
          <span>获取帮助</span>
        </el-button>
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

    <el-dialog
      v-model="helpVisible"
      title="系统配置帮助"
      width="min(580px, calc(100vw - 32px))"
      destroy-on-close
    >
      <div class="help-content">
        <p class="help-intro">目前数据库中登记了以下 3 项配置。键名需与列表完全一致，按说明填写对应的值。</p>
        <div class="help-list">
          <section v-for="item in helpItems" :key="item.key" class="help-item">
            <div class="help-item-heading">
              <strong>{{ item.title }}</strong>
              <el-tag size="small" effect="plain">{{ item.key }}</el-tag>
            </div>
            <p>{{ item.description }}</p>
            <div class="help-example"><span>填写示例</span><code>{{ item.example }}</code></div>
          </section>
        </div>
        <div class="help-note">
          <el-icon><InfoFilled /></el-icon>
          <span>访问令牌属于敏感信息，保存时请开启加密存储。不要把令牌发给他人或填写到公开内容中。</span>
        </div>
      </div>
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

.help-content { color: var(--color-text); }
.help-intro { margin-bottom: 16px; color: var(--color-text-secondary); font-size: .9rem; line-height: 1.7; }
.help-list { display: grid; gap: 10px; }
.help-item { padding: 14px 15px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg); }
.help-item-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.help-item-heading strong { font-size: .9rem; }
.help-item p { margin-top: 9px; color: var(--color-text-secondary); font-size: .82rem; line-height: 1.65; }
.help-example { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 10px; font-size: .76rem; }
.help-example span { color: var(--color-text-secondary); }
.help-example code { overflow-wrap: anywhere; color: var(--color-primary); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.help-note { display: flex; align-items: flex-start; gap: 8px; margin-top: 14px; padding: 11px 12px; border-radius: 7px; background: color-mix(in srgb, var(--color-primary) 9%, var(--color-surface)); color: var(--color-text-secondary); font-size: .78rem; line-height: 1.6; }
.help-note .el-icon { flex: 0 0 auto; margin-top: 2px; color: var(--color-primary); }
</style>
