<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchArticles, deleteArticle } from '@/api/articles'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const detailVisible = ref(false)
const detailRow = ref(null)

const router = useRouter()

const articles = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const search = ref('')
let searchTimer = null

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const { data } = await fetchArticles(params)
    articles.value = data.results
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

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？`, '确认', { type: 'warning' })
    await deleteArticle(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function onPageChange(p) { page.value = p; load() }
function onSizeChange(s) { pageSize.value = s; page.value = 1; load() }

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }
function statusTag(s) {
  const map = { published: 'success', draft: 'warning', private: 'danger' }
  return map[s] || 'info'
}
function statusText(s) {
  const map = { published: '已发布', draft: '草稿', private: '私密' }
  return map[s] || s
}

onMounted(() => { load() })
</script>

<template>
  <div>
    <div class="page-header">
      <h2>文章管理</h2>
      <div class="header-right">
        <el-input
          v-model="search"
          placeholder="搜索标题、正文、作者..."
          clearable
          style="width: 280px"
          :prefix-icon="Search"
          @input="onSearchChange"
          @clear="load"
        />
        <el-button type="primary" @click="router.push('/articles/edit')">新建文章</el-button>
      </div>
    </div>

    <el-table :data="articles" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="author_name" label="作者" width="100" />
      <el-table-column label="分类" width="120">
        <template #default="{ row }">{{ row.category?.name || '-' }}</template>
      </el-table-column>
      <el-table-column label="标签" width="200">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags" :key="t.id" size="small" :color="t.color" style="color:#fff;margin:0 2px;">{{ t.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="浏览" width="70" prop="view_count" />
      <el-table-column label="点赞" width="70" prop="like_count" />
      <el-table-column label="发布" width="110">
        <template #default="{ row }">{{ formatDate(row.published_at) }}</template>
      </el-table-column>
      <el-table-column label="最后修改" width="110">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="router.push(`/articles/edit/${row.id}`)">编辑</el-button>
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

    <el-dialog v-model="detailVisible" title="文章详情" width="560px" destroy-on-close>
      <el-descriptions v-if="detailRow" :column="2" border>
        <el-descriptions-item label="标题" :span="2">{{ detailRow.title }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ detailRow.author_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(detailRow.status)" size="small">{{ statusText(detailRow.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="分类">{{ detailRow.category?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="浏览">{{ detailRow.view_count ?? 0 }}</el-descriptions-item>
        <el-descriptions-item label="点赞">{{ detailRow.like_count ?? 0 }}</el-descriptions-item>
        <el-descriptions-item label="标签" :span="2">
          <el-tag v-for="t in detailRow.tags" :key="t.id" size="small" :color="t.color" style="color:#fff;margin:0 2px;">{{ t.name }}</el-tag>
          <span v-if="!detailRow.tags?.length">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(detailRow.published_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后修改">{{ formatDate(detailRow.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 16px; }
.page-header h2 { font-size: 1.3rem; white-space: nowrap; }
.header-right { display: flex; align-items: center; gap: 12px; }
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
