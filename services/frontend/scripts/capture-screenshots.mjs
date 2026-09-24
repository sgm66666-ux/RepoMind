import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const outputDirectory = path.resolve(frontendDirectory, '..', '..', 'docs', 'screenshots')
const baseUrl = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
const graphOnly = process.env.REPOMIND_SCREENSHOT_GRAPH_ONLY === '1'
const edgePaths = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]

await mkdir(outputDirectory, { recursive: true })

let browser
let lastError
for (const executablePath of edgePaths) {
  try {
    browser = await chromium.launch({ executablePath, headless: true })
    break
  } catch (error) {
    lastError = error
  }
}

if (!browser) {
  throw lastError || new Error('Microsoft Edge was not found.')
}

const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })

async function capture(name, fullPage = true) {
  await page.screenshot({ path: path.join(outputDirectory, name), fullPage })
  console.log(`captured ${name}`)
}

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '分析演示仓库' }).click()
  const analysisMessage = page.getByText('演示仓库分析完成')
  await analysisMessage.waitFor()
  await page.getByText('14', { exact: true }).first().waitFor()
  await analysisMessage.waitFor({ state: 'hidden' })
  await capture('overview.png')

  await page.getByRole('link', { name: '符号索引' }).click()
  await page.getByRole('row').filter({ hasText: 'demo.order.InventoryService.checkStock' }).click()
  await page.getByRole('heading', { name: 'demo.order.InventoryService.checkStock' }).waitFor()
  await page.waitForTimeout(350)
  await capture('symbol-explorer.png', false)
  await page.getByRole('button', { name: 'Close this dialog' }).click()

  await page.getByRole('link', { name: '调用关系图' }).click()
  await page.locator('.graph-canvas').waitFor()
  await capture('call-graph.png', false)

  if (!graphOnly) {
    await page.getByRole('link', { name: '故障定位' }).click()
    await page.getByRole('button', { name: '加载演示堆栈' }).click()
    const stackTraceMessage = page.getByText('已加载真实的 order-demo Stack Trace')
    await stackTraceMessage.waitFor()
    await stackTraceMessage.waitFor({ state: 'hidden' })
    await page.getByRole('button', { name: '开始定位' }).click()
    await page.getByRole('heading', { name: '可能原因' }).waitFor()
    await capture('fault-localization.png')

    await page.getByRole('link', { name: '代码智能助手' }).click()
    await page.getByRole('button', { name: '为什么 checkStock 出现空指针？' }).click()
    await page.getByRole('button', { name: '运行 Agent' }).click()
    const trace = page.getByTestId('agent-trace')
    const outcome = await Promise.race([
      trace.waitFor({ timeout: 210_000 }).then(() => 'trace'),
      page.locator('.agent-page .el-alert').waitFor({ timeout: 210_000 }).then(() => 'error'),
    ])
    if (outcome === 'error') throw new Error(`Real Agent request failed: ${await page.locator('.agent-page .el-alert').innerText()}`)
    await trace.getByText('已完成', { exact: true }).waitFor()
    await page.getByTestId('expert-details').locator('summary').click()
    await trace.getByText('ollama:', { exact: false }).first().waitFor()
    const steps = await trace.locator('.trace-step').count()
    if (steps < 2) throw new Error(`Real Agent produced only ${steps} Tool Calls; refusing to capture a misleading trace.`)
    await trace.getByText('searchSymbol', { exact: true }).first().waitFor()
    await trace.getByText('findCallees', { exact: true }).first().waitFor()
    await trace.getByText('readFile', { exact: true }).first().waitFor()
    await page.getByTestId('agent-context').waitFor()
    await capture('agent-real-trace.png')
  }
} finally {
  await browser.close()
}
