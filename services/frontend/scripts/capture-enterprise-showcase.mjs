import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendDirectory, '..', '..')
const showcasePath = path.join(repositoryRoot, 'demo', 'enterprise-order-showcase')
const screenshotDirectory = path.join(repositoryRoot, 'docs', 'screenshots')
const baseUrl = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
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
  await page.getByRole('link', { name: '项目概览' }).click()
  await page.getByText('仓库分析摘要').waitFor()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(3500)
  await page.screenshot({ path: path.join(screenshotDirectory, 'showcase-overview.png'), clip: { x: 0, y: 0, width: 1440, height: 725 }, animations: 'disabled' })

  await page.getByRole('link', { name: '调用关系图' }).click()
  await page.getByText('实线仅代表 resolved=true').waitFor()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(screenshotDirectory, 'showcase-call-graph-full.png'), fullPage: true, animations: 'disabled' })
  if (process.env.REPOMIND_CAPTURE_GRAPHS_ONLY !== '1') {
    await page.getByRole('link', { name: '代码智能助手' }).click()
    async function runAndCapture(question, filename, showRawWhenInvalid, requireDiagnosis = false) {
      await page.locator('#agent-question').fill(question)
      const responsePromise = page.waitForResponse(
        (response) => response.url().includes('/api/agent/chat') && response.request().method() === 'POST',
        { timeout: 240_000 },
      )
      await page.getByRole('button', { name: '运行 Agent' }).click()
      const response = await responsePromise
      if (!response.ok()) throw new Error(`Agent API returned ${response.status()}`)
      const result = await response.json()
      if (!result.provider?.startsWith('ollama:') || !Array.isArray(result.trace) || result.trace.length < 2) {
        throw new Error('Real Ollama trace was not returned; screenshot not saved.')
      }
      await page.getByTestId('agent-trace').waitFor()
      if (requireDiagnosis && !result.finalDiagnosis) {
        console.log(`${filename}: no validated FinalDiagnosis (${result.status}); screenshot not replaced`)
        return false
      }
      if (!result.finalDiagnosis && showRawWhenInvalid) {
        await page.getByTestId('raw-details').locator('summary').click()
      }
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.waitForTimeout(300)
      await page.screenshot({ path: path.join(screenshotDirectory, filename), fullPage: true, animations: 'disabled' })
      console.log(`${filename}: provider=${result.provider}, status=${result.status}, validatedDiagnosis=${Boolean(result.finalDiagnosis)}, tools=${result.trace.map((step) => step.tool).join(' -> ')}`)
      return true
    }

    if (process.env.REPOMIND_CAPTURE_RUNTIME_ONLY !== '1') {
      await runAndCapture(
        '追踪 OrderController.createOrder 到 InventoryRepository.findAvailableStock 的静态调用路径。',
        'showcase-call-chain.png', true,
      )
    }
    let runtimeCaptured = false
    for (let attempt = 0; attempt < 3 && !runtimeCaptured; attempt += 1) {
      runtimeCaptured = await runAndCapture(
        '为什么订单创建流程在 StockAllocator.allocate 库存预留阶段可能出现 NullPointerException？',
        'showcase-runtime-diagnosis.png', false, true,
      )
    }
    if (!runtimeCaptured) throw new Error('No validated runtime diagnosis after three real Ollama attempts.')
  }
} finally {
  await browser.close()
}
