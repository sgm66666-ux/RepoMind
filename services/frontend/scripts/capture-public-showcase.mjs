import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendDirectory, '..', '..')
const demoPath = path.join(repositoryRoot, 'demo', 'order-demo')
const screenshots = path.join(repositoryRoot, 'docs', 'screenshots')
const baseUrl = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
const edgePaths = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]

let browser
for (const executablePath of edgePaths) {
  try {
    browser = await chromium.launch({ executablePath, headless: true })
    break
  } catch { /* Try the other standard Edge installation path. */ }
}
if (!browser) throw new Error('Microsoft Edge was not found.')

const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  // This affects only the headless capture page, never the normal application.
  await page.addStyleTag({ content: '* { cursor: none !important; }' })
  await page.mouse.move(0, 0)

  await page.getByRole('link', { name: '代码仓库' }).click()
  await page.getByPlaceholder('输入后端可访问的仓库绝对路径').fill(demoPath)
  await page.getByRole('button', { name: '开始分析' }).click()
  await page.locator('.analysis-status.success').waitFor({ timeout: 30_000 })

  await page.getByRole('link', { name: '代码智能助手' }).click()
  await page.locator('#agent-question').fill('为什么InventoryService.checkStock出现NullPointerException？')
  const agentResponse = page.waitForResponse(
    (response) => response.url().includes('/api/agent/chat') && response.request().method() === 'POST',
    { timeout: 240_000 },
  )
  await page.getByRole('button', { name: '运行 Agent' }).click()
  const apiResponse = await agentResponse
  if (!apiResponse.ok()) throw new Error(`Agent API returned ${apiResponse.status()}`)
  const result = await apiResponse.json()
  if (!result.provider?.startsWith('ollama:') || result.status !== 'COMPLETED' ||
      !result.plan || !result.finalDiagnosis || !Array.isArray(result.trace) || result.trace.length < 2 ||
      result.trace.some((step) => !step.observation)) {
    throw new Error('Real Ollama Plan/Tool/Observation response was not complete; no screenshot was saved.')
  }
  await page.getByTestId('final-diagnosis').waitFor()
  const details = page.getByTestId('expert-details')
  await details.locator('summary').click()
  await page.getByTestId('agent-plan').waitFor()
  await details.locator('.trace-step').first().waitFor()
  await page.mouse.move(0, 0)
  // The sticky application header can cover the top of an element screenshot.
  const headerVisibility = await page.addStyleTag({ content: '.topbar { visibility: hidden !important; }' })
  await details.screenshot({ path: path.join(screenshots, 'public-agent-trace.png'), animations: 'disabled' })
  await headerVisibility.evaluate((element) => element.remove())

  await page.getByRole('link', { name: '项目概览' }).click()
  await page.getByText('仓库分析摘要').waitFor()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(500)
  await page.mouse.move(0, 0)
  await page.screenshot({ path: path.join(screenshots, 'public-overview.png'), fullPage: true, animations: 'disabled' })

  await page.getByRole('link', { name: '调用关系图' }).click()
  await page.getByText('实线仅代表 resolved=true').waitFor()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(500)
  await page.mouse.move(0, 0)
  await page.screenshot({ path: path.join(screenshots, 'public-call-graph.png'), fullPage: true, animations: 'disabled' })

  console.log(`Real provider: ${result.provider}; tools: ${result.trace.map((step) => step.tool).join(' -> ')}`)
  console.log('Captured public-agent-trace.png, public-overview.png, public-call-graph.png')
} finally {
  await browser.close()
}
