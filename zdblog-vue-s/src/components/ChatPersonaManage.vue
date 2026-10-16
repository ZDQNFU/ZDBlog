<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchPersonas,
  fetchPersona,
  createPersona,
  updatePersona,
  deletePersona,
} from '@/api/chats'

const personas = ref([]),
  loading = ref(false),
  saving = ref(false),
  search = ref('')
const total = ref(0),
  page = ref(1),
  pageSize = ref(10)
const visible = ref(false),
  editingId = ref(null),
  formRef = ref(null)
const form = reactive({
  name: '',
  description: '',
  system_prompt: '',
  greeting: '',
  is_active: true,
  sort_order: 0,
  tools: ['get_weather', 'search_func'],
})
const rules = {
  name: [{ required: true, whitespace: true, message: '请输入人物名称', trigger: 'blur' }],
  system_prompt: [
    { required: true, whitespace: true, message: '请输入人物 Prompt', trigger: 'blur' },
  ],
}
function errorText(e) {
  const data = e.response?.data
  return data ? Object.values(data).flat().join('；') : e.message || '操作失败'
}
async function load() {
  loading.value = true
  try {
    const { data } = await fetchPersonas({
      search: search.value,
      page: page.value,
      page_size: pageSize.value,
    })
    personas.value = data.results || []
    total.value = data.count || 0
    const lastPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (page.value > lastPage) {
      page.value = lastPage
      await load()
    }
  } catch (e) {
    ElMessage.error(errorText(e))
  } finally {
    loading.value = false
  }
}
async function edit(persona) {
  try {
    const data = persona
      ? (await fetchPersona(persona.id)).data
      : {
          name: '',
          description: '',
          system_prompt: '',
          greeting: '',
          is_active: true,
          sort_order: 0,
          tools: ['get_weather', 'search_func'],
        }
    Object.assign(form, data)
    editingId.value = persona?.id || null
    if (!persona) page.value = 1
    visible.value = true
  } catch (e) {
    ElMessage.error(errorText(e))
  }
}
async function save() {
  if (saving.value || !(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    const payload = Object.fromEntries(
      ['name', 'description', 'system_prompt', 'greeting', 'is_active', 'sort_order', 'tools'].map(
        (key) => [key, form[key]],
      ),
    )
    if (editingId.value) await updatePersona(editingId.value, payload)
    else await createPersona(payload)
    visible.value = false
    ElMessage.success('人物已保存，新建聊天时生效')
    await load()
  } catch (e) {
    ElMessage.error(errorText(e))
  } finally {
    saving.value = false
  }
}
async function remove(persona) {
  try {
    await ElMessageBox.confirm(
      `删除人物「${persona.name}」？已有聊天会保留人物设定和历史记录。`,
      '删除人物',
      { type: 'warning' },
    )
    await deletePersona(persona.id)
    total.value = Math.max(0, total.value - 1)
    if (personas.value.length === 1 && page.value > 1) page.value--
    ElMessage.success('人物已删除')
    await load()
  } catch (e) {
    if (e instanceof Error) ElMessage.error(errorText(e))
  }
}
function changePage(value) {
  page.value = value
  load()
}
function changePageSize(value) {
  pageSize.value = value
  page.value = 1
  load()
}
function searchPersonas() {
  page.value = 1
  load()
}
onMounted(load)
</script>

<template>
  <section class="persona-section">
    <div class="persona-header">
      <div>
        <h3>人物管理</h3>
        <p>管理 C 端可选人物，修改设定对新聊天生效。</p>
      </div>
      <el-button type="primary" @click="edit(null)">新增人物</el-button>
    </div>
    <div class="persona-search">
      <el-input
        v-model="search"
        placeholder="搜索人物名称或简介"
        clearable
        @keyup.enter="searchPersonas"
        @clear="searchPersonas"
      /><el-button :loading="loading" @click="searchPersonas">查询</el-button>
    </div>
    <el-table :data="personas" v-loading="loading" border stripe>
      <el-table-column prop="name" label="人物名称" min-width="120" />
      <el-table-column prop="description" label="人物简介" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="90"
        ><template #default="{ row }"
          ><el-tag :type="row.is_active ? 'success' : 'info'">{{
            row.is_active ? '启用' : '停用'
          }}</el-tag></template
        ></el-table-column
      >
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column label="操作" width="180"
        ><template #default="{ row }"
          ><el-button size="small" @click="edit(row)">查看 / 编辑</el-button
          ><el-button type="danger" size="small" @click="remove(row)">删除</el-button></template
        ></el-table-column
      >
    </el-table>
    <el-pagination
      v-if="total"
      class="persona-pagination"
      background
      layout="total, sizes, prev, pager, next, jumper"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      :page-sizes="[10, 20, 50]"
      @current-change="changePage"
      @size-change="changePageSize"
    />
    <el-dialog
      v-model="visible"
      :title="editingId ? '编辑人物' : '新增人物'"
      width="min(760px, 95vw)"
      destroy-on-close
      :close-on-click-modal="!saving"
      :show-close="!saving"
      :close-on-press-escape="!saving"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="saving">
        <el-form-item label="可用工具（可全部取消）">
          <el-checkbox-group v-model="form.tools">
            <el-checkbox value="list_articles">文章列表 / 时间查询</el-checkbox>
            <el-checkbox value="count_articles">文章数量统计</el-checkbox>
            <el-checkbox value="get_article">文章正文阅读</el-checkbox>
            <el-checkbox value="search_blog">站内知识库 RAG</el-checkbox>
            <el-checkbox value="search_func">联网搜索</el-checkbox>
            <el-checkbox value="get_weather">天气查询</el-checkbox>
            <el-checkbox value="analyze_sentiment">明日香情感分析</el-checkbox>
          </el-checkbox-group>
          <p style="font-size: 12px; color: var(--color-text-secondary)">
            工具配置随人物快照保存在新聊天中。
          </p>
        </el-form-item>
        <el-form-item label="人物名称" prop="name"
          ><el-input v-model="form.name" maxlength="80" show-word-limit
        /></el-form-item>
        <el-form-item label="人物简介"
          ><el-input
            v-model="form.description"
            maxlength="500"
            type="textarea"
            :rows="2"
            show-word-limit
        /></el-form-item>
        <el-form-item label="人物 System Prompt" prop="system_prompt"
          ><el-input
            v-model="form.system_prompt"
            maxlength="20000"
            type="textarea"
            :rows="10"
            show-word-limit
            placeholder="描述人物身份、语气、行为和工具使用规则"
        /></el-form-item>
        <el-form-item label="开场白"
          ><el-input
            v-model="form.greeting"
            maxlength="2000"
            type="textarea"
            :rows="3"
            show-word-limit
        /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
        <el-form-item label="排序（越小越靠前）"
          ><el-input-number v-model="form.sort_order" :min="-100000" :max="100000"
        /></el-form-item>
      </el-form>
      <template #footer
        ><el-button :disabled="saving" @click="visible = false">取消</el-button
        ><el-button type="primary" :loading="saving" @click="save">保存人物</el-button></template
      >
    </el-dialog>
  </section>
</template>

<style scoped>
.persona-section {
  margin-bottom: 32px;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--color-border);
}
.persona-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.persona-header h3 {
  margin: 0;
  font-size: 1.05rem;
}
.persona-header p {
  color: var(--color-text-secondary);
  font-size: 13px;
}
.persona-search {
  display: flex;
  gap: 10px;
  max-width: 460px;
  margin: 16px 0;
}
.persona-pagination {
  justify-content: center;
  margin-top: 16px;
}
</style>
