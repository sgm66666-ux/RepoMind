import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const base = process.env.REPOMIND_FRONTEND_URL || 'http://127.0.0.1:5173'
const output = path.join(root, 'logs', 'gateway-removal-integration')
await mkdir(output, { recursive: true })
const scenarios = [
  { id: 'inventory', repository: 'demo/order-demo', question: '为什么InventoryService.checkStock出现NullPointerException？' },
  { id: 'register', repository: 'demo/repomind-agent-test-demo/call-chain-demo', question: '追踪UserService.register到ConfigRepository.getTemplate的调用路径。' },
  { id: 'price', repository: 'demo/repomind-agent-test-demo/logic-bug-demo', question: '为什么订单价格计算错误？' },
  { id: 'enterprise', repository: 'demo/enterprise-order-showcase', question: '为什么订单创建流程在 StockAllocator.allocate 库存预留阶段可能出现 NullPointerException？' },
]
const browser = await chromium.launch({
  executablePath: process.env.REPOMIND_BROWSER_EXECUTABLE || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
})
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
const pageErrors = []
page.on('pageerror', (error) => pageErrors.push(error.message))
const report = { frontend: base, providerMode: 'real Ollama, no mocked responses', pageErrors, scenarios: [] }
let pendingAgent = false
try {
  await page.goto(base, { waitUntil: 'networkidle' })
  const health = await page.request.get(base + '/api/health')
  assert.equal(health.status(), 200)
  assert.deepEqual(await health.json(), { status: 'ok', service: 'python-service' })
  for (const scenario of scenarios) {
    const record = { id: scenario.id, question: scenario.question, transportPassed: false, uiTracePassed: false, scenarioPassed: false }
    report.scenarios.push(record)
    try {
      await page.getByRole('link', { name: '代码仓库', exact: true }).click()
      await page.getByPlaceholder('输入后端可访问的仓库绝对路径').fill(path.join(root, scenario.repository))
      const analysisPromise = page.waitForResponse((response) =>
        response.url().endsWith('/api/repositories/analyze') && response.request().method() === 'POST')
      await page.getByRole('button', { name: '开始分析', exact: true }).click()
      const analysisResponse = await analysisPromise
      assert.equal(analysisResponse.status(), 200)
      record.analysis = await analysisResponse.json()
      await page.locator('.analysis-status.success').waitFor()
      const graphResponse = await page.request.get(base + '/api/call-graph?includeUnresolved=false')
      assert.equal(graphResponse.status(), 200)
      const graph = await graphResponse.json()
      record.graph = { nodes: graph.nodes.length, edges: graph.edges.length }
      await page.getByRole('link', { name: '符号索引', exact: true }).click()
      await page.getByRole('link', { name: '调用关系图', exact: true }).click()
      if (scenario.id === 'inventory') {
        await page.getByRole('link', { name: '故障定位', exact: true }).click()
        const demoPromise = page.waitForResponse((response) => response.url().endsWith('/api/demo/order-demo'))
        await page.getByRole('button', { name: '加载演示堆栈' }).click()
        await demoPromise
        await page.waitForFunction(() => document.querySelector('textarea')?.value.includes('InventoryService.java:12'))
        const faultPromise = page.waitForResponse((response) => response.url().endsWith('/api/fault-localization'))
        await page.getByRole('button', { name: '开始定位', exact: true }).click()
        const fault = await (await faultPromise).json()
        assert.equal(fault.status, 'LOCATED')
        assert.equal(fault.targetFile, 'InventoryService.java')
        assert.equal(fault.stackFrame.lineNumber, 12)
        await page.getByTestId('fault-result').waitFor()
        record.faultLocalization = 'LOCATED InventoryService.java:12'
      }
      if (scenario.id === 'register') {
        const names = ['UserService.register', 'EmailService.sendEmail', 'TemplateService.render', 'ConfigRepository.getTemplate']
        const ids = names.map((name) => graph.nodes.find((node) => node.qualifiedName === name)?.id)
        assert.ok(ids.every(Boolean))
        for (let index = 0; index < ids.length - 1; index++) {
          assert.ok(graph.edges.some((edge) => edge.resolved && edge.sourceSymbolId === ids[index] && edge.targetSymbolId === ids[index + 1]))
        }
        record.staticCallPath = names
      }
      if (scenario.id === 'enterprise') {
        assert.equal(record.analysis.sourceFileCount, 60)
        assert.equal(record.analysis.symbolCount, 205)
        assert.equal(record.analysis.relationCount, 579)
        assert.equal(record.analysis.resolvedCallCount, 100)
        assert.equal(record.analysis.unresolvedCallCount, 59)
      }
      await page.getByRole('link', { name: '代码智能助手', exact: true }).click()
      await page.locator('#agent-question').fill(scenario.question)
      const responsePromise = page.waitForResponse((response) =>
        response.url().endsWith('/api/agent/chat') && response.request().method() === 'POST', { timeout: 220_000 })
      pendingAgent = true
      await page.getByRole('button', { name: '运行 Agent', exact: true }).click()
      const httpResponse = await responsePromise
      const result = await httpResponse.json()
      pendingAgent = false
      await writeFile(path.join(output, scenario.id + '-response.json'), JSON.stringify(result, null, 2) + '\n')
      record.httpStatus = httpResponse.status()
      record.provider = result.provider
      record.agentStatus = result.status
      record.diagnosisStatus = result.diagnosisStatus
      record.tools = (result.trace || []).map((step) => step.tool)
      assert.equal(httpResponse.status(), 200)
      assert.match(result.provider, /^ollama:qwen2\.5-coder:14b:/)
      assert.ok(result.trace.length >= 2)
      assert.ok(result.trace.every((step) => step.observation && step.tool && typeof step.success === 'boolean'))
      record.transportPassed = true
      await page.getByTestId('agent-trace').waitFor()
      await page.getByTestId('expert-details').locator('summary').click()
      assert.equal(await page.locator('.trace-step').count(), result.trace.length)
      await page.getByTestId('agent-plan').waitFor()
      await page.getByTestId('raw-details').locator('summary').click()
      await page.getByTestId('raw-model-output').waitFor()
      record.uiTracePassed = true
      await page.screenshot({ path: path.join(output, scenario.id + '.png'), fullPage: true })
      assert.equal(result.status, 'COMPLETED')
      assert.equal(result.diagnosisStatus, 'VALID')
      await page.getByTestId('final-diagnosis').waitFor()
      const facts = result.finalDiagnosis.evidence || []
      if (scenario.id === 'inventory') {
        assert.ok(facts.some((fact) => fact.code === 'return null;' && fact.source_tool === 'readFile'))
        assert.ok(facts.some((fact) => fact.code === 'if (stock.available) {' && fact.source_tool === 'readFile'))
      } else if (scenario.id === 'register') {
        assert.deepEqual(result.finalDiagnosis.call_chain.map((name) => name.split('.').slice(-2).join('.')), record.staticCallPath)
      } else if (scenario.id === 'price') {
        assert.ok(result.executionState.missing_evidence.includes('business_expectation'))
        await page.getByText('业务规则证据不足', { exact: true }).waitFor()
      } else {
        assert.equal(result.crossFileEvidence?.final_diagnosis_complete, true)
        assert.ok(new Set(facts.filter((fact) => fact.source_tool === 'readFile').map((fact) => fact.file)).size >= 2)
      }
      record.scenarioPassed = true
    } catch (error) {
      record.error = error.message
      if (pendingAgent) break
    }
    console.log(JSON.stringify(record))
  }
} finally {
  report.passed = report.scenarios.length === scenarios.length &&
    report.scenarios.every((record) => record.scenarioPassed && record.transportPassed && record.uiTracePassed) &&
    pageErrors.length === 0
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n')
  await browser.close()
}
console.log('Report: ' + path.join(output, 'report.json'))
if (!report.passed) process.exitCode = 1
