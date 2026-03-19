import api from './index'

// 종목 검색
export const searchStock = (query) => api.get('/stock/search', { params: { query } })

// 종목 분석 시작
export const analyzeStock = (ticker, companyName) => api.post('/stock/analyze', { ticker, company_name: companyName })

// 분석 상태 확인
export const getAnalyzeStatus = (taskId) => api.get(`/stock/analyze/${taskId}/status`)

// 시뮬레이션 시작
export const startSimulation = (taskId) => api.post('/stock/simulate', { task_id: taskId })

// 시뮬레이션 상태
export const getSimulationStatus = (simId) => api.get(`/stock/simulate/${simId}/status`)

// 보고서 생성
export const generateReport = (simId) => api.post(`/stock/report/${simId}`)

// 보고서 조회
export const getReport = (reportId) => api.get(`/stock/report/${reportId}`)
