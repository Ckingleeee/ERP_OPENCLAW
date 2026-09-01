/**
 * 对话 API 模块
 *
 * 提供流式对话、中断恢复和会话状态查询接口
 */

import { apiFetch } from './http.js'

const API_BASE = '/api/chat'

export class ChatStreamError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'ChatStreamError'
    this.code = options.code || 'CHAT_STREAM_ERROR'
    this.retryable = options.retryable === true
    this.threadId = options.threadId || null
    this.partialContent = options.partialContent || ''
  }
}

function normalizeChatError(error, threadId = null) {
  if (error instanceof ChatStreamError || error?.name === 'AbortError') {
    return error
  }

  const rawMessage = String(error?.message || error || '')
  const isTransportFailure = error instanceof TypeError || [
    'network error',
    'failed to fetch',
    'load failed',
    'network request failed',
    'connection was closed'
  ].some(marker => rawMessage.toLowerCase().includes(marker))

  if (isTransportFailure) {
    return new ChatStreamError(
      '与服务器的连接意外中断，后台任务可能仍在执行，请先查看当前会话结果，避免重复操作。',
      { code: 'NETWORK_DISCONNECTED', retryable: false, threadId }
    )
  }

  return new ChatStreamError(
    rawMessage || '请求处理失败，请稍后重试。',
    { code: 'REQUEST_FAILED', retryable: false, threadId }
  )
}

async function createHttpError(response, action) {
  let message = `${action}失败（HTTP ${response.status}）`
  try {
    const payload = await response.clone().json()
    message = payload.detail || payload.message || message
  } catch {
    // Non-JSON error responses use the stable status-based message above.
  }
  return new ChatStreamError(message, {
    code: `HTTP_${response.status}`,
    retryable: response.status === 408 || response.status === 429 || response.status >= 500
  })
}

/**
 * 流式对话
 *
 * 使用 fetch + ReadableStream 接收流式响应（支持 POST 请求）
 *
 * @param {string} message - 用户消息
 * @param {string|null} threadId - 会话 ID，为空则创建新会话
 * @param {Object} callbacks - 回调函数对象
 * @param {Function} callbacks.onToken - 接收到 token 时的回调 (content: string, source: string) => void
 * @param {Function} callbacks.onToolStart - 工具开始调用时的回调 (tool: object) => void
 * @param {Function} callbacks.onToolArgs - 工具参数片段的回调 (args: string, source: string) => void
 * @param {Function} callbacks.onToolResult - 工具结果返回时的回调 (tool: object) => void
 * @param {Function} callbacks.onToolEnd - 工具调用结束时的回调 (tool: object) => void
 * @param {Function} callbacks.onInterrupt - 检测到中断时的回调 (interruptData: object) => void
 * @param {Function} callbacks.onDone - 流结束时的回调 (data: object) => void
 * @param {Function} callbacks.onSession - 服务端确认会话 ID 时的回调 (threadId: string) => void
 * @param {Function} callbacks.onError - 发生错误时的回调 (error: Error) => void
 * @param {AbortSignal} signal - 可选的 AbortSignal，用于取消请求
 * @returns {Promise} 返回包含 thread_id, content, tool_calls 的结果
 */
export async function streamChat(message, threadId = null, callbacks = {}, signal = null) {
  // 用于收集完整内容
  let fullContent = ''
  let toolCalls = []
  // 工具调用栈，支持嵌套工具调用（主代理调 task → 子代理调工具）
  let toolStack = []

  try {
    // 使用 fetch 发送 POST 请求，支持 AbortController
    const response = await apiFetch(`${API_BASE}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        thread_id: threadId
      }),
      signal: signal  // 支持取消请求
    })

    if (!response.ok) {
      throw await createHttpError(response, '请求')
    }

    return await processChatStream(response, threadId, callbacks, fullContent, toolCalls, toolStack)

  } catch (error) {
    if (error.name === 'AbortError') {
      // 用户主动取消，返回已收集的内容
      console.log('[ChatAPI] 请求已被用户取消')
      const result = {
        thread_id: threadId,
        content: fullContent,
        tool_calls: toolCalls,
        aborted: true
      }
      callbacks.onDone?.(result)
      return result
    }
    const normalizedError = normalizeChatError(error, threadId)
    console.error('[ChatAPI] 流式请求失败:', normalizedError)
    callbacks.onError?.(normalizedError)
    throw normalizedError
  }
}

/**
 * 流式中断恢复
 *
 * 当中断发生后，前端收集用户决策/补充数据，通过此函数恢复 Agent 执行。
 *
 * @param {string} threadId - 会话 ID
 * @param {Object} resumeData - 恢复数据，格式取决于中断类型：
 *   - 数据补充: { supplement: "用户输入的补充信息" }
 *   - HITL 审批: { decisions: [{ type: "approve" }] } 或 [{ type: "reject" }]
 * @param {Object} callbacks - 回调函数对象（与 streamChat 相同）
 * @param {AbortSignal} signal - 可选的 AbortSignal，用于取消请求
 * @returns {Promise} 返回包含 thread_id, content, tool_calls 的结果
 */
export async function resumeChat(threadId, resumeData, callbacks = {}, signal = null) {
  let fullContent = ''
  let toolCalls = []
  let toolStack = []

  try {
    const response = await apiFetch(`${API_BASE}/${threadId}/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ resume: resumeData }),
      signal: signal
    })

    if (!response.ok) {
      throw await createHttpError(response, '恢复请求')
    }

    return await processChatStream(response, threadId, callbacks, fullContent, toolCalls, toolStack)

  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('[ChatAPI] 恢复请求已被用户取消')
      const result = {
        thread_id: threadId,
        content: fullContent,
        tool_calls: toolCalls,
        aborted: true
      }
      callbacks.onDone?.(result)
      return result
    }
    const normalizedError = normalizeChatError(error, threadId)
    console.error('[ChatAPI] 恢复请求失败:', normalizedError)
    callbacks.onError?.(normalizedError)
    throw normalizedError
  }
}

/**
 * 处理流式响应的内部函数（streamChat 和 resumeChat 共用）
 */
export async function processChatStream(response, threadId, callbacks, fullContent, toolCalls, toolStack) {
  // 获取 reader 来读取流
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    let readResult
    try {
      readResult = await reader.read()
    } catch (error) {
      const normalizedError = normalizeChatError(error, threadId)
      normalizedError.partialContent = fullContent
      throw normalizedError
    }
    const { done, value } = readResult

    if (done) {
      break
    }

    // 解码数据
    buffer += decoder.decode(value, { stream: true })

    // 处理缓冲区中的数据（按行分割）
    const lines = buffer.split('\n')
    buffer = lines.pop() // 保留未完成的行

    for (const line of lines) {
      if (!line.trim() || !line.startsWith('data:')) {
        continue
      }

      let data
      try {
        data = JSON.parse(line.slice(5).trim())
      } catch (parseError) {
        console.warn('[ChatAPI] 解析 SSE 数据失败:', parseError)
        continue
      }

      switch (data.type) {
          case 'session':
            threadId = data.thread_id || threadId
            callbacks.onSession?.(threadId)
            break

          case 'token':
            // AI 生成的文本片段
            fullContent += data.content
            callbacks.onToken?.(data.content, data.source)
            break

          case 'tool_start':
            // 工具开始调用，压入栈
            const newTool = {
              id: data.tool_call_id,
              name: data.tool_name,
              args: '',
              source: data.source,
              text: '',
              images: []
            }
            toolStack.push(newTool)
            callbacks.onToolStart?.(newTool)
            break

          case 'tool_args':
            // 工具参数片段，更新栈顶工具
            if (toolStack.length > 0) {
              toolStack[toolStack.length - 1].args += data.args
            }
            callbacks.onToolArgs?.(data.args, data.source)
            break

          case 'tool_result':
            // 工具执行结果，弹出栈顶工具并更新
            if (toolStack.length > 0) {
              const finished = toolStack.pop()
              finished.text = data.text || ''
              finished.images = data.images || []
              toolCalls.push({ ...finished })
              callbacks.onToolResult?.(finished)
            }
            break

          case 'tool_end':
            // 工具调用结束
            callbacks.onToolEnd?.({
              id: data.tool_call_id,
              name: data.tool_name,
              source: data.source
            })
            break

          case 'interrupt':
            // ★ Human-in-the-Loop 中断检测
            console.log('[ChatAPI] 检测到中断:', data.interrupt_type)
            callbacks.onInterrupt?.(data)
            // 中断事件后流会结束，返回当前已收集的内容
            return {
              thread_id: data.thread_id || threadId,
              content: fullContent,
              tool_calls: toolCalls,
              interrupted: true,
              interrupt_data: data
            }

          case 'done':
            // 流结束
            const result = {
              thread_id: data.thread_id,
              content: data.content || fullContent,
              tool_calls: toolCalls,
              interrupted: data.interrupted || false
            }
            callbacks.onDone?.(result)
            return result

          case 'error':
            throw new ChatStreamError(
              data.message || '服务端处理请求失败。',
              {
                code: data.code || 'SERVER_STREAM_ERROR',
                retryable: data.retryable === true,
                threadId: data.thread_id || threadId,
                partialContent: fullContent
              }
            )

          default:
            break
      }
    }
  }

  // A normal stream always ends with done or interrupt. EOF alone means truncation.
  throw new ChatStreamError(
    '与服务器的流式连接提前结束，后台任务状态暂时无法确认，请先查看会话结果。',
    {
      code: 'STREAM_INCOMPLETE',
      retryable: false,
      threadId,
      partialContent: fullContent
    }
  )
}

/**
 * 获取会话状态
 *
 * @param {string} threadId - 会话 ID
 * @returns {Promise} 返回会话状态对象
 */
export async function getChatState(threadId) {
  const response = await apiFetch(`${API_BASE}/${threadId}`)

  if (!response.ok) {
    throw new Error('获取会话状态失败')
  }

  return response.json()
}

/**
 * 获取会话历史状态列表
 *
 * @param {string} threadId - 会话 ID
 * @param {number} limit - 返回的最大状态数量
 * @returns {Promise} 返回状态历史列表
 */
export async function getChatHistory(threadId, limit = 50) {
  const response = await apiFetch(`${API_BASE}/${threadId}/history?limit=${limit}`)

  if (!response.ok) {
    throw new Error('获取会话历史失败')
  }

  return response.json()
}
