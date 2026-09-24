import { access, mkdir, writeFile } from 'node:fs/promises'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright-core'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const root = path.resolve(frontendDirectory, '..', '..')
const screenshotDirectory = path.join(root, 'docs', 'screenshots')
const runDirectory = path.join(root, 'docs', 'release', 'demo-runs')
const frontendUrl = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
const scenarioId = process.argv[2]
const replaceBaseline = process.argv.includes('--replace-baseline')
const scenarios = {
  inventory: {
    repository: 'demo/order-demo',
    question: '为什么InventoryService.checkStock出现NullPointerException？',
    screenshot: 'inventory-npe-final-diagnosis.png',
  },
  register: {
    repository: 'demo/repomind-agent-test-demo/call-chain-demo',
    question: '追踪UserService.register到ConfigRepository.getTemplate的调用路径。',
    screenshot: 'register-call-chain.png',
  },
  price: {
    repository: 'demo/repomind-agent-test-demo/logic-bug-demo',
    question: '为什么订单价格计算错误？',
    screenshot: 'price-evidence-insufficient.png',
  },
}
if (!Object.hasOwn(scenarios, scenarioId)) {
  throw new Error('Choose exactly one real demo: inventory, register, or price')
}
const scenario = scenarios[scenarioId]
const repository = path.join(root, scenario.repository)
let screenshotPath = path.join(screenshotDirectory, scenario.screenshot)
await mkdir(screenshotDirectory, { recursive: true })
await mkdir(runDirectory, { recursive: true })
if (!replaceBaseline) {
  try {
    await access(screenshotPath)
    screenshotPath = path.join(screenshotDirectory,
      `${path.parse(scenario.screenshot).name}-${randomUUID().slice(0, 8)}.png`)
  } catch (error) { if (error.code !== 'ENOENT') throw error }
}

let browser
for (const executablePath of [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]) {
  try { browser = await chromium.launch({ executablePath, headless: true }); break }
  catch { /* Continue with the other installed Edge path. */ }
}
if (!browser) throw new Error('Installed Microsoft Edge is required; no browser will be downloaded.')

const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 })
try {
  await page.goto(frontendUrl, { waitUntil: 'networkidle' })
  await page.getByRole('link', { name: '代码仓库' }).click()
  await page.getByPlaceholder('输入后端可访问的仓库绝对路径').fill(repository)
  await page.getByRole('button', { name: '开始分析' }).click()
  await page.locator('.analysis-status.success').waitFor({ timeout: 60_000 })
  await page.getByRole('link', { name: '代码智能助手' }).click()
  await page.locator('#agent-question').fill(scenario.question)
  const resultPromise = page.waitForResponse(
    response => response.url().endsWith('/api/agent/chat') && response.request().method() === 'POST',
    { timeout: 220_000 },
  )
  await page.getByRole('button', { name: '运行 Agent' }).click()
  const httpResponse = await resultPromise
  const rawBody = await httpResponse.text()
  let result
  try { result = JSON.parse(rawBody) }
  catch { result = { parseError: 'Non-JSON API response', rawBody } }
  const stamp = new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')
  const runPath = path.join(runDirectory, `${stamp}-${scenarioId}.json`)
  await writeFile(runPath, JSON.stringify({ scenarioId, repository, question: scenario.question,
    statusCode: httpResponse.status(), capturedAt: new Date().toISOString(), response: result }, null, 2), { flag: 'wx' })

  if (!httpResponse.ok()) throw new Error(`Real Agent HTTP ${httpResponse.status()}; raw response saved: ${runPath}`)
  if (!String(result.provider || '').startsWith('ollama:qwen2.5-coder:14b')) {
    throw new Error(`Not a real expected Ollama response; saved: ${runPath}`)
  }
  if (result.status !== 'COMPLETED' || result.diagnosisStatus !== 'VALID' || !result.finalDiagnosis) {
    throw new Error(`No validated FinalDiagnosis (${result.status}/${result.diagnosisStatus}); saved: ${runPath}`)
  }
  if (!result.trace?.some(step => step.success && step.tool === 'searchSymbol')) {
    throw new Error(`No real successful Symbol search; saved: ${runPath}`)
  }
  const diagnosis = result.finalDiagnosis
  const evidenceCodes = diagnosis.evidence.map(item => item.code)
  if (scenarioId === 'inventory' &&
      (!evidenceCodes.includes('return null;') || !evidenceCodes.includes('if (stock.available) {') ||
       !result.trace.some(step => step.success && step.tool === 'readFile'))) {
    throw new Error(`Inventory source/usage evidence incomplete; saved: ${runPath}`)
  }
  if (scenarioId === 'register' &&
      (result.executionState?.graph_path_evidence?.length !== 3 ||
       diagnosis.call_chain.join(' → ') !==
         'UserService.register → EmailService.sendEmail → TemplateService.render → ConfigRepository.getTemplate')) {
    throw new Error(`Register AST path incomplete; saved: ${runPath}`)
  }
  if (scenarioId === 'price' &&
      (!evidenceCodes.includes('return price + quantity * discount;') ||
       /price\s*\*\s*quantity\s*\*\s*discount/i.test(diagnosis.root_cause + ' ' + diagnosis.fix_suggestion) ||
       !result.executionState?.missing_evidence?.includes('business_expectation'))) {
    throw new Error(`Price evidence or uncertainty guard failed; saved: ${runPath}`)
  }
  const card = page.getByTestId('final-diagnosis')
  await card.waitFor({ timeout: 10_000 })
  await page.getByTestId('agent-context').waitFor({ state: 'visible', timeout: 15_000 })
  await card.getByText('关键证据 · FACT').waitFor()
  await card.getByText('原因分析 · INFERENCE').waitFor()
  if (scenarioId === 'price') await card.getByText('业务规则证据不足').waitFor()
  const expert = page.getByTestId('expert-details')
  const raw = page.getByTestId('raw-details')
  if (await expert.evaluate(element => element.open) || await raw.evaluate(element => element.open)) {
    throw new Error(`Advanced details unexpectedly open; saved: ${runPath}`)
  }
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) {
    throw new Error(`Page overflows horizontally; saved: ${runPath}`)
  }
  await page.evaluate(async () => {
    await document.fonts.ready
    window.scrollTo(0, 0)
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  })
  const layout = await page.evaluate(() => ({ scrollY: window.scrollY,
    pageHeight: document.documentElement.scrollHeight,
    diagnosisHeight: document.querySelector('[data-testid="final-diagnosis"]')?.getBoundingClientRect().height }))
  if (layout.scrollY !== 0 || !layout.diagnosisHeight || layout.pageHeight < layout.diagnosisHeight) {
    throw new Error(`Page layout unsettled before capture: ${JSON.stringify(layout)}; saved: ${runPath}`)
  }
  await page.mouse.move(0, 0)
  await page.screenshot({ path: screenshotPath, fullPage: true })
  await expert.locator('summary').click()
  await raw.locator('summary').click()
  if (!(await expert.evaluate(element => element.open)) || !(await raw.evaluate(element => element.open)) ||
      !(await raw.getByTestId('raw-model-output').isVisible())) {
    throw new Error(`Advanced Trace or raw model output failed to expand; saved: ${runPath}`)
  }
  await expert.locator('summary').click()
  await raw.locator('summary').click()
  if (await expert.evaluate(element => element.open) || await raw.evaluate(element => element.open)) {
    throw new Error(`Details failed to collapse; saved: ${runPath}`)
  }
  console.log(JSON.stringify({ scenarioId, screenshotPath, runPath, provider: result.provider,
    toolTrace: result.trace.map(step => step.tool), diagnosisStatus: result.diagnosisStatus,
    evidenceCodes, callChain: diagnosis.call_chain }, null, 2))
} finally {
  await browser.close()
}
