import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendDirectory, '..', '..')
const demoPath = path.join(repositoryRoot, 'demo', 'repomind-agent-test-demo', 'logic-bug-demo')
const screenshotPath = path.join(repositoryRoot, 'docs', 'screenshots', 'agent-plan-price-real.png')
const userScreenshotPath = path.join(repositoryRoot, 'docs', 'screenshots', 'agent-final-diagnosis-real.png')
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
  await page.getByRole('link', { name: '代码仓库' }).click()
  await page.getByPlaceholder('输入后端可访问的仓库绝对路径').fill(demoPath)
  await page.getByRole('button', { name: '开始分析' }).click()
  await page.locator('.analysis-status.success').waitFor()

  await page.getByRole('link', { name: '代码智能助手' }).click()
  await page.locator('#agent-question').fill('为什么订单价格计算错误？')
  await page.getByRole('button', { name: '运行 Agent' }).click()
  const trace = page.getByTestId('agent-trace')
  const outcome = await Promise.race([
    trace.waitFor({ timeout: 210_000 }).then(() => 'trace'),
    page.locator('.agent-page .el-alert').waitFor({ timeout: 210_000 }).then(() => 'error'),
  ])
  if (outcome === 'error') throw new Error(`Real Agent request failed: ${await page.locator('.agent-page .el-alert').innerText()}`)

  const diagnosis = page.getByTestId('final-diagnosis')
  await diagnosis.waitFor()
  await diagnosis.getByText('return price + quantity * discount;').waitFor()
  await trace.getByText('已完成', { exact: true }).waitFor()
  if (await page.getByTestId('raw-details').evaluate((element) => element.open)) {
    throw new Error('Raw model output was expanded by default.')
  }
  await page.getByTestId('agent-context').waitFor()
  await mkdir(path.dirname(screenshotPath), { recursive: true })
  await page.screenshot({ path: userScreenshotPath, fullPage: true })

  await page.getByTestId('expert-details').locator('summary').click()
  const plan = page.getByTestId('agent-plan')
  await plan.getByText('BUSINESS_LOGIC_ERROR').waitFor()
  await trace.getByText('ollama:', { exact: false }).first().waitFor()
  const tools = await trace.locator('.trace-step h3').allTextContents()
  if (tools.length < 3 || !tools.includes('searchSymbol') || !tools.includes('findCallers') || !tools.includes('readFile')) {
    throw new Error(`Real trace did not cover the requested business-logic path: ${tools.join(' -> ')}`)
  }
  await page.screenshot({ path: screenshotPath, fullPage: true })
  console.log(`captured ${userScreenshotPath}`)
  console.log(`captured ${screenshotPath}`)
  console.log(`real tools: ${tools.join(' -> ')}`)
} finally {
  await browser.close()
}
