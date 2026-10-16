<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { createArticle, generateArticleSummary, uploadImage } from '@/api/articles'
import { fetchCategories } from '@/api/categories'
import { fetchTags } from '@/api/tags'

defineProps({
  variant: {
    type: String,
    default: 'default',
  },
})

const router = useRouter()
const emit = defineEmits(['saved'])
const visible = ref(false)
const processing = ref(false)
const loadingOptions = ref(false)
const optionsError = ref(false)
const markdownFile = ref(null)
const imageFiles = ref([])
const unresolvedImages = ref([])
const categories = ref([])
const tags = ref([])
const cover = ref('')
const category = ref(null)
const selectedTags = ref([])
const markdownInput = ref(null)
const imageInput = ref(null)
const directoryInput = ref(null)

const selectedImageCount = computed(() => imageFiles.value.length)

function isMarkdown(file) {
  return /\.(md|markdown)$/i.test(file.name)
}

function isImage(file) {
  return file.type?.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(file.name)
}

function onMarkdownSelected(event) {
  const [file] = Array.from(event.target.files || [])
  if (file) markdownFile.value = file
  event.target.value = ''
}

function onImagesSelected(event) {
  const files = Array.from(event.target.files || []).filter(isImage)
  const existing = new Set(imageFiles.value.map(file => `${file.webkitRelativePath || file.name}:${file.size}:${file.lastModified}`))
  imageFiles.value = [
    ...imageFiles.value,
    ...files.filter(file => !existing.has(`${file.webkitRelativePath || file.name}:${file.size}:${file.lastModified}`)),
  ]
  event.target.value = ''
}

function onDirectorySelected(event) {
  const files = Array.from(event.target.files || [])
  const markdowns = files.filter(isMarkdown)
  if (markdowns.length !== 1) {
    ElMessage.error('请选择只包含一篇 Markdown 文章的文件夹')
    event.target.value = ''
    return
  }
  markdownFile.value = markdowns[0]
  imageFiles.value = files.filter(file => file !== markdowns[0] && isImage(file))
  unresolvedImages.value = []
  ElMessage.success(`已读取文章和 ${imageFiles.value.length} 张图片`)
  event.target.value = ''
}

function parseArticle(markdown) {
  const lines = markdown.replace(/^\uFEFF/, '').split(/\r?\n/)
  const titleIndex = lines.findIndex(line => line.trim())
  if (titleIndex < 0 || !/^ {0,3}#\s+\S/.test(lines[titleIndex])) {
    throw new Error('文章第一行需要是一级标题，例如「# 标题」')
  }

  const title = lines[titleIndex].trim().replace(/^#\s+/, '').replace(/\s+#+\s*$/, '').trim()
  if (title.length > 200) throw new Error('文章标题不能超过 200 个字符')
  lines.splice(titleIndex, 1)
  const content = lines.join('\n').trim()
  if (!content) throw new Error('标题下面还没有文章正文')
  if (content.length > 30000) throw new Error('文章正文超过 30000 字，暂时无法生成摘要')
  return { title, content }
}

function decodePath(value) {
  const unwrapped = value.startsWith('<') && value.endsWith('>') ? value.slice(1, -1) : value
  const unescaped = unwrapped.replace(/\\([\\()[\]])/g, '$1')
  try {
    return decodeURIComponent(unescaped)
  } catch {
    return unescaped
  }
}

function isDirectImageSource(source) {
  return /^(https?:|data:|blob:|\/\/)/i.test(source)
    || /^\/(media|static|uploads|assets|images)\//i.test(source)
}

function normalizedPath(value) {
  return decodePath(value)
    .replace(/^file:\/*/i, '')
    .replace(/\\/g, '/')
    .replace(/^\/?([a-z]:\/)/i, '$1')
    .replace(/^[a-z]:/i, '')
    .replace(/[?#].*$/, '')
    .replace(/^\/+|\/+$/g, '')
    .split('/')
    .filter(part => part && part !== '.')
    .join('/')
    .toLocaleLowerCase()
}

function findLocalImage(source, markdownFile, files) {
  const wanted = normalizedPath(source)
  const directory = normalizedPath(markdownFile.webkitRelativePath || markdownFile.name)
    .split('/')
    .slice(0, -1)
    .join('/')
  const filePaths = new Map()
  const fileNames = new Map()

  for (const file of files) {
    const path = normalizedPath(file.webkitRelativePath || file.name)
    if (!filePaths.has(path)) filePaths.set(path, [])
    filePaths.get(path).push(file)
    const name = normalizedPath(file.name)
    if (!fileNames.has(name)) fileNames.set(name, [])
    fileNames.get(name).push(file)
  }

  const exact = filePaths.get(wanted)
  if (exact?.length === 1) return exact[0]
  const relative = directory ? filePaths.get(`${directory}/${wanted}`) : null
  if (relative?.length === 1) return relative[0]
  const basename = wanted.split('/').pop()
  const matches = fileNames.get(basename) || []
  if (matches.length === 1) return matches[0]
  if (matches.length > 1 || exact?.length > 1 || relative?.length > 1) {
    throw new Error(`图片路径「${source}」匹配到多个文件，请选择包含目录结构的文章文件夹`)
  }
  return null
}

async function rewriteLocalImages(markdown, sourceFile) {
  const pattern = /(!\[[^\]]*\]\()(<[^>]+>|(?:\\.|[^)])+?)(\s+(?:"[^"]*"|'[^']*'))?(\))/g
  const matches = [...markdown.matchAll(pattern)]
  const imageMap = new Map()
  const uploads = new Map()
  const missing = []

  for (const match of matches) {
    const rawSource = match[2]
    const source = decodePath(rawSource)
    if (isDirectImageSource(source)) continue

    const file = findLocalImage(source, sourceFile, imageFiles.value)
    if (!file) {
      missing.push(source)
      continue
    }
    imageMap.set(rawSource, file)
  }

  unresolvedImages.value = [...new Set(missing)]
  if (unresolvedImages.value.length) {
    throw new Error('请先选择 Markdown 引用的本地图片，再重新导入')
  }

  for (const [rawSource, file] of imageMap) {
    if (!uploads.has(file)) {
      const { data } = await uploadImage(file)
      uploads.set(file, data.url)
    }
    imageMap.set(rawSource, uploads.get(file))
  }

  return markdown.replace(pattern, (full, prefix, rawSource, title = '', closing) => {
    const uploadedUrl = imageMap.get(rawSource)
    if (!uploadedUrl) return full
    const replacement = rawSource.startsWith('<') ? `<${uploadedUrl}>` : uploadedUrl
    return `${prefix}${replacement}${title}${closing}`
  })
}

function openDialog() {
  markdownFile.value = null
  imageFiles.value = []
  unresolvedImages.value = []
  categories.value = []
  tags.value = []
  cover.value = ''
  category.value = null
  selectedTags.value = []
  visible.value = true
  loadOptions()
}

async function loadOptions() {
  loadingOptions.value = true
  optionsError.value = false
  try {
    const [categoryResponse, tagResponse] = await Promise.all([
      fetchCategories({ page_size: 1000 }),
      fetchTags({ page_size: 1000 }),
    ])
    categories.value = categoryResponse.data.results || categoryResponse.data
    tags.value = tagResponse.data.results || tagResponse.data
  } catch {
    optionsError.value = true
    ElMessage.error('分类或标签加载失败，请关闭后重试')
  } finally {
    loadingOptions.value = false
  }
}

async function importArticle() {
  if (!markdownFile.value) {
    ElMessage.warning('请先选择 Markdown 文件或文章文件夹')
    return
  }
  if (!cover.value.trim()) {
    ElMessage.warning('请填写封面图片 URL')
    return
  }
  if (!category.value) {
    ElMessage.warning('请选择文章分类')
    return
  }
  if (!selectedTags.value.length) {
    ElMessage.warning('请至少选择一个文章标签')
    return
  }

  processing.value = true
  unresolvedImages.value = []
  try {
    const { title, content } = parseArticle(await markdownFile.value.text())
    const content_md = await rewriteLocalImages(content, markdownFile.value)
    const { data } = await generateArticleSummary({ title, content_md })
    await createArticle({
      title,
      content_md,
      summary: data.summary,
      status: 'published',
      cover: cover.value.trim(),
      category: category.value || null,
      tags: selectedTags.value,
    })
    visible.value = false
    ElMessage.success('文章已生成摘要并发布')
    emit('saved')
    if (router.currentRoute.value.path !== '/articles') await router.push('/articles')
  } catch (error) {
    const responseData = error.response?.data
    const detail = responseData?.detail
      || (responseData ? Object.values(responseData).flat().join('，') : '')
      || error.message
      || '导入失败，请稍后重试'
    ElMessage.error(detail)
  } finally {
    processing.value = false
  }
}
</script>

<template>
  <div class="article-markdown-import">
    <button type="button" class="import-button" :class="variant" @click="openDialog">
      <el-icon><Upload /></el-icon>
      上传文章
    </button>

    <el-dialog v-model="visible" title="上传并发布 Markdown 文章" width="600px" append-to-body :close-on-click-modal="false">
      <div class="import-help">
        <p>首行一级标题（<code># 标题</code>）会作为文章标题并从正文中移除；摘要由 DeepSeek 生成，发布状态默认为“已发布”。</p>
        <p>HTTP 图片和站内 <code>/media/</code>、<code>/static/</code> 等路径会保留。本地图片会上传到已配置的 GitHub 图床。</p>
      </div>

      <div v-loading="loadingOptions" class="import-form">
        <div class="picker-row">
          <el-button @click="markdownInput?.click()">选择 Markdown</el-button>
          <span class="picked-file">{{ markdownFile?.webkitRelativePath || markdownFile?.name || '尚未选择 .md 文件' }}</span>
        </div>
        <div class="picker-row">
          <el-button @click="imageInput?.click()">选择关联图片</el-button>
          <span class="picked-file">已选择 {{ selectedImageCount }} 张图片</span>
        </div>
        <div class="picker-row folder-row">
          <el-button link type="primary" @click="directoryInput?.click()">或选择包含 Markdown 和图片的文件夹</el-button>
        </div>

        <div class="form-field">
          <label for="article-cover-url">封面图片 URL</label>
          <el-input id="article-cover-url" v-model="cover" placeholder="手动填写封面图片 URL" />
        </div>
        <div class="form-field">
          <label>分类</label>
          <el-select v-model="category" clearable placeholder="选择分类">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </div>
        <div class="form-field">
          <label>标签</label>
          <el-select v-model="selectedTags" multiple clearable placeholder="选择标签">
            <el-option v-for="item in tags" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </div>
      </div>

      <div v-if="unresolvedImages.length" class="missing-images">
        找不到以下本地图片，请选择关联图片后重试：
        <ul><li v-for="path in unresolvedImages" :key="path">{{ path }}</li></ul>
      </div>

      <template #footer>
        <el-button :disabled="processing" @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="processing" :disabled="loadingOptions || optionsError" @click="importArticle">生成摘要并发布</el-button>
      </template>

      <input ref="markdownInput" class="hidden-input" type="file" accept=".md,.markdown,text/markdown" @change="onMarkdownSelected" />
      <input ref="imageInput" class="hidden-input" type="file" accept="image/*" multiple @change="onImagesSelected" />
      <input ref="directoryInput" class="hidden-input" type="file" webkitdirectory directory multiple @change="onDirectorySelected" />
    </el-dialog>
  </div>
</template>

<style scoped>
.import-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--el-color-primary);
  border-radius: 6px;
  background: var(--el-color-primary);
  color: #fff;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: background .18s ease, border-color .18s ease;
}

.import-button:hover { background: var(--el-color-primary-light-3); border-color: var(--el-color-primary-light-3); }
.import-button.dashboard { background: var(--color-surface); border-color: var(--dash-line); color: var(--color-text); }
.import-button.dashboard:hover { border-color: var(--dash-accent); color: var(--dash-accent); background: var(--color-surface); }
.article-markdown-import { display: inline-flex; }
.import-help { margin-bottom: 18px; color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.7; }
.import-help p { margin: 0 0 6px; }
.import-help code { color: var(--el-color-primary); }
.import-form { display: grid; gap: 4px; }
.picker-row { display: flex; align-items: center; gap: 12px; margin: 12px 0; }
.picked-file { min-width: 0; overflow: hidden; color: var(--el-text-color-secondary); text-overflow: ellipsis; white-space: nowrap; }
.folder-row { margin-top: 2px; }
.form-field { margin-top: 8px; }
.form-field label { display: block; margin-bottom: 6px; color: var(--el-text-color-regular); font-size: 13px; font-weight: 500; }
.form-field .el-select { width: 100%; }
.missing-images { margin-top: 16px; padding: 10px 12px; border-radius: 6px; background: var(--el-color-warning-light-9); color: var(--el-color-warning-dark-2); font-size: 13px; overflow-wrap: anywhere; }
.missing-images ul { margin: 6px 0 0; padding-left: 20px; }
.hidden-input { display: none; }

@media (max-width: 600px) {
  :deep(.el-dialog) { width: min(600px, 94vw) !important; }
  .picker-row { align-items: flex-start; flex-direction: column; gap: 6px; }
}
</style>
