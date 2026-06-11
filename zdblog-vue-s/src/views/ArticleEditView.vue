<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { fetchArticle, createArticle, updateArticle, uploadImage } from '@/api/articles'
import { fetchCategories } from '@/api/categories'
import { fetchTags } from '@/api/tags'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTheme } from '@/composables/useTheme'
import { ArrowLeft } from '@element-plus/icons-vue'

const { isDark } = useTheme()

const route = useRoute()
const router = useRouter()

const editId = computed(() => route.params.id || null)
const isEdit = computed(() => !!editId.value)

const loading = ref(false)
const saving = ref(false)
const categories = ref([])
const tags = ref([])
const showMeta = ref(true)

const form = ref({
  title: '',
  content_md: '',
  summary: '',
  cover: '',
  status: 'draft',
  category: null,
  tags: [],
})

async function loadOptions() {
  const [catRes, tagRes] = await Promise.all([
    fetchCategories({ page_size: 1000 }),
    fetchTags({ page_size: 1000 }),
  ])
  categories.value = catRes.data.results || catRes.data
  tags.value = tagRes.data.results || tagRes.data
}

async function loadArticle() {
  if (!editId.value) return
  loading.value = true
  try {
    const { data } = await fetchArticle(editId.value)
    form.value = {
      title: data.title,
      content_md: data.content_md || '',
      summary: data.summary || '',
      cover: data.cover || '',
      status: data.status || 'draft',
      category: data.category?.id || null,
      tags: data.tags?.map(t => t.id) || [],
    }
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.category) delete payload.category
    if (isEdit.value) {
      await updateArticle(editId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createArticle(payload)
      ElMessage.success('创建成功')
    }
    router.push('/articles')
  } catch (e) {
    const detail = e.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : Object.values(e.response?.data || {}).flat().join(', ')
    ElMessage.error(msg || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleUploadImg(files, callback) {
  try {
    const urls = []
    for (const file of files) {
      const { data } = await uploadImage(file, editId.value || '')
      urls.push(data.url)
    }
    callback(urls)
  } catch (e) {
    const detail = e.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : '图片上传失败'
    ElMessage.error(msg)
  }
}

function goBack() {
  if (form.value.content_md || form.value.title) {
    ElMessageBox.confirm('未保存的内容将丢失，确定返回？', '确认', { type: 'warning' })
      .then(() => router.push('/articles'))
      .catch(() => {})
  } else {
    router.push('/articles')
  }
}

onMounted(() => { loadOptions(); loadArticle() })
</script>

<template>
  <div class="edit-page">
    <header class="edit-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <h2>{{ isEdit ? '编辑文章' : '新建文章' }}</h2>
      </div>
      <div class="header-right">
        <el-button @click="showMeta = !showMeta">
          {{ showMeta ? '隐藏' : '显示' }}元数据
        </el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEdit ? '保存修改' : '发布文章' }}
        </el-button>
      </div>
    </header>

    <div class="edit-body" v-loading="loading">
      <div class="editor-area">
        <MdEditor
          v-model="form.content_md"
          :preview="true"
          :theme="isDark ? 'dark' : 'light'"
          language="en-US"
          :onUploadImg="handleUploadImg"
          style="height: 100%"
        />
      </div>

      <transition name="meta-slide">
        <aside v-show="showMeta" class="meta-panel">
          <h3>文章信息</h3>

          <div class="meta-field">
            <label>标题</label>
            <el-input v-model="form.title" placeholder="文章标题" />
          </div>

          <div class="meta-field">
            <label>摘要</label>
            <el-input v-model="form.summary" type="textarea" :rows="3" placeholder="文章摘要" />
          </div>

          <div class="meta-field">
            <label>封面图片 URL</label>
            <el-input v-model="form.cover" placeholder="https://..." />
          </div>

          <div class="meta-field">
            <label>状态</label>
            <el-select v-model="form.status">
              <el-option label="草稿" value="draft" />
              <el-option label="已发布" value="published" />
              <el-option label="私密" value="private" />
            </el-select>
          </div>

          <div class="meta-field">
            <label>分类</label>
            <el-select v-model="form.category" clearable placeholder="选择分类">
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </div>

          <div class="meta-field">
            <label>标签</label>
            <el-select v-model="form.tags" multiple placeholder="选择标签">
              <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </div>
        </aside>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.edit-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  z-index: 100;
}

.edit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 52px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-left h2 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text);
}

.header-right {
  display: flex;
  gap: 8px;
}

.edit-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-area {
  flex: 1;
  min-width: 0;
  height: 100%;
}

.meta-panel {
  width: 320px;
  flex-shrink: 0;
  border-left: 1px solid var(--el-border-color-light);
  padding: 20px;
  overflow-y: auto;
  background: var(--color-bg);
}

.meta-panel h3 {
  font-size: 1rem;
  margin-bottom: 20px;
  color: var(--el-text-color-primary);
}

.meta-field {
  margin-bottom: 18px;
}

.meta-field label {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  margin-bottom: 5px;
}

.meta-field .el-select {
  width: 100%;
}

.meta-slide-enter-active,
.meta-slide-leave-active {
  transition: width 0.25s ease, opacity 0.25s ease;
}
.meta-slide-enter-from,
.meta-slide-leave-to {
  width: 0;
  opacity: 0;
}
</style>
