import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendDirectory, '..', '..')
const showcasePath = path.join(repositoryRoot, 'demo', 'enterprise-order-showcase')
const screenshotPath = path.join(repositoryRoot, 'docs', 'screenshots', 'showcase-cross-file-diagnosis.png')
const baseUrl = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
const question = '为什么订单创建流程在 StockAllocator.allocate 库存预留阶段可能出现 NullPointerException？'
const edgePaths = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]

let browser
for (const executablePath of edgePaths) {
  try { browser = await chromium.launch({ executablePath, headless: true }); break }
  catch { /* Try the other standard Edge installation path. */ }
}
if (!browser) throw new Error('Microsoft Edge was not found.')

const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.addStyleTag({ content: '* { cursor: none !important; }' })
  await page.mouse.move(0, 0)
  await page.getByRole('link', { name: '代码仓库' }).click()
  await page.getByPlaceholder('输入后端可访问的仓库绝对路径').fill(showcasePath)
  await page.getByRole('button', { name: '开始分析' }).click()
  await page.locator('.analysis-status.success').waitFor({ timeout: 60_000 })
  await page.getByRole('link', { name: '代码智能助手' }).click()
  await page.locator('#agent-question').fill(question)
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes('/api/agent/chat') && response.request().method() === 'POST',
    { timeout: 240_000 },
  )
  await page.getByRole('button', { name: '运行 Agent' }).click()
  const response = await responsePromise
  if (!response.ok()) throw new Error(`Agent API returned ${response.status()}`)
  const result = await response.json()
  const evidence = result.finalDiagnosis?.evidence || []
  const files = new Set(evidence.filter((item) => item.source_tool === 'readFile').map((item) => item.file))
  if (!result.provider?.startsWith('ollama:qwen2.5-coder:14b:') ||
      result.diagnosisStatus !== 'VALID' || !result.crossFileEvidence?.final_diagnosis_complete ||
      ![...files].some((file) => file.endsWith('/StockAllocator.java')) ||
      ![...files].some((file) => file.endsWith('/InMemoryInventoryRepository.java'))) {
    throw new Error(`No verified cross-file FinalDiagnosis; screenshot not saved. Status=${result.diagnosisStatus}`)
  }
  await page.getByTestId('final-diagnosis').waitFor()
  await page.mouse.move(0, 0)
  await page.getByTestId('final-diagnosis').screenshot({ path: screenshotPath, animations: 'disabled' })
  console.log(`Captured real cross-file diagnosis: ${[...files].join(', ')}; ${result.trace.length} Tool calls`)
} finally {
  await browser.close()
}
