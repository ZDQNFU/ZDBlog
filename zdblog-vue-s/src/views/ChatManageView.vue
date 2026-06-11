<script setup>
import { ref, onMounted } from 'vue'
import { fetchChatUsers, fetchChatUserDetail, clearChatHistory, trimChatHistory } from '@/api/chats'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const users = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
let searchTimer = null

const detailVisible = ref(false)
const detailUser = ref(null)
const detailMessages = ref([])
const detailLoading = ref(false)

const trimVisible = ref(false)
const trimUserId = ref(null)
const trimUsername = ref('')
const trimDays = ref(30)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const { data } = await fetchChatUsers(params)
    users.value = data.results || data
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

async function openDetail(user) {
  detailUser.value = user
  detailVisible.value = true
  detailMessages.value = []
  detailLoading.value = true
  try {
    const { data } = await fetchChatUserDetail(user.id)
    detailMessages.value = data.messages
  } catch {
    ElMessage.error('加载聊天记录失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleClear(user) {
  try {
    await ElMessageBox.confirm(`确定清空用户「${user.username}」的全部聊天记录？`, '确认', { type: 'warning' })
    const { data } = await clearChatHistory(user.id)
    ElMessage.success(data.detail || '已清空')
    load()
  } catch { /* cancelled */ }
}

function openTrim(user) {
  trimUserId.value = user.id
  trimUsername.value = user.username
  trimDays.value = 30
  trimVisible.value = true
}

async function handleTrim() {
  try {
    const { data } = await trimChatHistory(trimUserId.value, trimDays.value)
    ElMessage.success(data.detail || '已清理')
    trimVisible.value = false
    load()
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '操作失败')
  }
}

function formatTime(ts) {
  if (!ts) return '-'
  try {
    return new Date(ts).toLocaleString('zh-CN')
  } catch {
    return ts
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>聊天管理</h2>
      <div class="header-right">
        <el-input
          v-model="search"
          placeholder="搜索用户名..."
          clearable
          style="width: 220px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
      </div>
    </div>

    <el-table :data="users" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="message_count" label="消息数" width="100" align="center" />
      <el-table-column label="最后活跃" min-width="170">
        <template #default="{ row }">{{ formatTime(row.last_active) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="280">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openDetail(row)">详情</el-button>
          <el-button size="small" @click="openTrim(row)">保留天数</el-button>
          <el-button size="small" type="danger" @click="handleClear(row)">清空</el-button>
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

    <div v-if="!loading && !users.length" class="empty-text">暂无聊天记录</div>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" :title="`${detailUser?.username} 的聊天记录`" width="700px" destroy-on-close>
      <div v-loading="detailLoading" class="detail-body">
        <div v-if="!detailMessages.length && !detailLoading" class="empty-text">暂无消息</div>
        <div
          v-for="(m, i) in detailMessages"
          :key="i"
          :class="['msg-row', m.role]"
        >
          <div class="msg-bubble">
            <span class="msg-role">{{ m.role === 'user' ? '用户' : 'AI' }}</span>
            <p class="msg-content">{{ m.content }}</p>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- Trim dialog -->
    <el-dialog v-model="trimVisible" :title="`保留聊天记录 — ${trimUsername}`" width="400px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="保留天数">
          <el-input-number v-model="trimDays" :min="1" :max="365" />
        </el-form-item>
        <p class="trim-hint">仅保留最近 {{ trimDays }} 天的聊天记录，更早的记录将被删除。</p>
      </el-form>
      <template #footer>
        <el-button @click="trimVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTrim">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 16px; }
.page-header h2 { font-size: 1.3rem; white-space: nowrap; }
.header-right { display: flex; align-items: center; gap: 12px; }

.empty-text { text-align: center; color: var(--color-text-secondary); padding: 48px 0; }

.detail-body { max-height: 500px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }

.msg-row { display: flex; }
.msg-row.user { justify-content: flex-end; }
.msg-row.ai { justify-content: flex-start; }

.msg-bubble {
  background-color: antiquewhite;
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.88rem;
  line-height: 1.6;
}
.msg-row.user .msg-bubble { background: var(--color-primary); color: #fff; }
.msg-row.ai .msg-bubble { background: var(--color-surface); color: var(--color-text); }

.msg-role {
  display: block;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
  font-weight: 600;
}
.msg-content { white-space: pre-wrap; word-break: break-word; margin: 0; }

.trim-hint { font-size: 0.82rem; color: var(--color-text-secondary); margin-top: 8px; }
</style>
