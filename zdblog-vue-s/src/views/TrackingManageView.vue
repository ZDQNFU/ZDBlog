<script setup>
import { ref, onMounted } from 'vue'
import { fetchVisitors, fetchVisitorDetail, deleteVisitor, batchDeleteVisitors } from '@/api/tracking'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const visitors = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
let searchTimer = null

const detailVisible = ref(false)
const detailVisitor = ref(null)
const detailLoading = ref(false)

const selectedKeys = ref([])

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const { data } = await fetchVisitors(params)
    visitors.value = data.results || data
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

function onSelectChange(rows) {
  selectedKeys.value = rows.map(r => r.session_key)
}

async function openDetail(row) {
  detailVisitor.value = null
  detailVisible.value = true
  detailLoading.value = true
  try {
    const { data } = await fetchVisitorDetail(row.session_key)
    detailVisitor.value = data
  } catch {
    ElMessage.error('加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除该访问记录？`, '确认', { type: 'warning' })
    await deleteVisitor(row.session_key)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

async function handleBatchDelete() {
  if (!selectedKeys.value.length) {
    ElMessage.warning('请先选择要删除的记录')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedKeys.value.length} 条记录？`, '批量删除', { type: 'warning' })
    await batchDeleteVisitors(selectedKeys.value)
    ElMessage.success('已删除')
    selectedKeys.value = []
    load()
  } catch { /* cancelled */ }
}

function formatTime(ts) {
  if (!ts) return '-'
  try {
    return new Date(ts).toLocaleString('zh-CN')
  } catch {
    return ts
  }
}

function getMethodTag(method) {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', PATCH: '', DELETE: 'danger' }
  return map[method] || 'info'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>访问日志</h2>
      <div class="header-right">
        <el-input
          v-model="search"
          placeholder="搜索 IP 或用户名..."
          clearable
          style="width: 240px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-button type="danger" :disabled="!selectedKeys.length" @click="handleBatchDelete">
          批量删除 {{ selectedKeys.length ? `(${selectedKeys.length})` : '' }}
        </el-button>
      </div>
    </div>

    <el-table
      :data="visitors"
      v-loading="loading"
      stripe
      border
      style="width:100%"
      @selection-change="onSelectChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="ip_address" label="IP 地址" min-width="130" />
      <el-table-column prop="username" label="用户" width="100">
        <template #default="{ row }">{{ row.username || '匿名' }}</template>
      </el-table-column>
      <el-table-column label="开始时间" min-width="165">
        <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" min-width="165">
        <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
      </el-table-column>
      <el-table-column label="停留时长" min-width="110" align="center">
        <template #default="{ row }">
          {{ row.time_on_site != null ? `${row.time_on_site} 秒` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="访问页面数" width="100" align="center">
        <template #default="{ row }">{{ row.pageviews?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" class="detail-btn" @click="openDetail(row)">详情</el-button>
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

    <div v-if="!loading && !visitors.length" class="empty-text">暂无访问记录</div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" :title="`访问详情 — ${detailVisitor?.ip_address || ''}`" width="700px" destroy-on-close>
      <div v-loading="detailLoading">
        <template v-if="detailVisitor">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="IP 地址">{{ detailVisitor.ip_address }}</el-descriptions-item>
            <el-descriptions-item label="用户">{{ detailVisitor.username || '匿名' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ formatTime(detailVisitor.start_time) }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ formatTime(detailVisitor.end_time) }}</el-descriptions-item>
            <el-descriptions-item label="停留时长">{{ detailVisitor.time_on_site ?? '-' }} 秒</el-descriptions-item>
            <el-descriptions-item label="Session Key" :span="2">{{ detailVisitor.session_key }}</el-descriptions-item>
            <el-descriptions-item label="User Agent" :span="2">
              <span style="word-break:break-all;font-size:0.8rem;">{{ detailVisitor.user_agent || '-' }}</span>
            </el-descriptions-item>
          </el-descriptions>

          <h4 style="margin:20px 0 12px;">浏览页面 ({{ detailVisitor.pageviews?.length || 0 }})</h4>
          <el-table :data="detailVisitor.pageviews" size="small" border max-height="300">
            <el-table-column prop="method" label="方法" width="70">
              <template #default="{ row }">
                <el-tag :type="getMethodTag(row.method)" size="small">{{ row.method }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="url" label="URL" min-width="250" />
            <el-table-column label="访问时间" width="165">
              <template #default="{ row }">{{ formatTime(row.view_time) }}</template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 16px; }
.page-header h2 { font-size: 1.3rem; white-space: nowrap; }
.header-right { display: flex; align-items: center; gap: 12px; }
.pagination-wrap { margin-top: 20px; display: flex; justify-content: center; }
.empty-text { text-align: center; color: var(--color-text-secondary); padding: 48px 0; }

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
