import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendDirectory, '..', '..')
const showcasePath = path.join(repositoryRoot, 'demo', 'enterprise-order-showcase')
const screenshotPath = path.join(repositoryRoot, 'docs', 'screenshots', 'showcase-call-graph-focus.png')
const baseUrl = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
const focusNames = new Set([
  'OrderController.createOrder',
  'OrderApplicationService.createOrder',
  'OrderService.processOrder',
  'PricingService.calculateOrderPrice',
  'InventoryService.reserveInventory',
  'PaymentService.pay',
])
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
let focusedGraph
try {
  // Only the screenshot browser filters a real API response. No edge or Symbol is invented.
  await page.route('**/api/call-graph?*', async (route) => {
    const response = await route.fetch()
    const graph = await response.json()
    const nodes = graph.nodes.filter((node) => focusNames.has(node.qualifiedName.split('.').slice(-2).join('.')))
    const ids = new Set(nodes.map((node) => node.id))
    const edges = graph.edges.filter((edge) => edge.resolved && ids.has(edge.sourceSymbolId) && ids.has(edge.targetSymbolId))
    focusedGraph = { nodes, edges }
    if (nodes.length !== focusNames.size || edges.length < 5) {
      throw new Error(`Unexpected focus graph: ${nodes.length} nodes, ${edges.length} edges`)
    }
    await route.fulfill({ response, json: { ...graph, nodes, edges } })
  })
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.addStyleTag({ content: '* { cursor: none !important; }' })
  await page.mouse.move(0, 0)
  await page.getByRole('link', { name: '代码仓库' }).click()
  await page.getByPlaceholder('输入后端可访问的仓库绝对路径').fill(showcasePath)
  await page.getByRole('button', { name: '开始分析' }).click()
  await page.locator('.analysis-status.success').waitFor({ timeout: 60_000 })
  if (!focusedGraph) throw new Error('Real Call Graph API was not observed.')
  await page.getByRole('link', { name: '调用关系图' }).click()
  await page.getByText('实线仅代表 resolved=true').waitFor()
  await page.locator('.graph-canvas').evaluate((element) => { element.style.height = '620px' })
  await page.evaluate(() => window.dispatchEvent(new Event('resize')))
  await page.waitForTimeout(200)
  await page.getByRole('button', { name: '放大' }).click()
  const canvas = await page.locator('.graph-canvas').boundingBox()
  if (!canvas) throw new Error('Call Graph canvas was not rendered.')
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2)
  await page.mouse.down()
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2 + 100, { steps: 8 })
  await page.mouse.up()
  await page.getByRole('button', { name: '放大' }).click()
  await page.mouse.move(0, 0)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(500)
  await page.locator('.graph-panel').screenshot({ path: screenshotPath, animations: 'disabled' })
  console.log(`Captured actual focus graph: ${focusedGraph.nodes.length} nodes, ${focusedGraph.edges.length} resolved edges`)
} finally {
  await browser.close()
}
