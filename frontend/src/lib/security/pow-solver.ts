/**
 * PoW (Proof of Work) 求解器（Phase 3）
 *
 * 当请求被风控引擎判定为 CHALLENGE 时，前端需要解一个计算谜题。
 * 使用 Web Worker 在后台线程计算，不阻塞 UI。
 */

export interface PowChallenge {
  challenge_id: string
  algorithm: string
  prefix: string
  data: string
  difficulty: number
  expires_at: number
}

/**
 * 在主线程中解 PoW（备选方案，当 Worker 不可用时）
 */
async function solveInMainThread(data: string, difficulty: number): Promise<number> {
  const prefix = '0'.repeat(difficulty)
  let nonce = 0

  while (nonce < 100_000_000) {
    const input = `${data}${nonce}`
    const encoded = new TextEncoder().encode(input)
    const hashBuffer = await crypto.subtle.digest('SHA-256', encoded)
    const hashArray = new Uint8Array(hashBuffer)
    const hashHex = Array.from(hashArray)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')

    if (hashHex.startsWith(prefix)) {
      return nonce
    }
    nonce++

    // 每 1000 次让出主线程
    if (nonce % 1000 === 0) {
      await new Promise((r) => setTimeout(r, 0))
    }
  }

  throw new Error('PoW: 超过最大尝试次数')
}

/**
 * 解 PoW 挑战
 * @returns nonce 值
 */
export async function solvePow(challenge: PowChallenge): Promise<number> {
  // 检查是否过期
  if (Date.now() / 1000 > challenge.expires_at) {
    throw new Error('PoW: 挑战已过期')
  }

  // 尝试使用 Web Worker（如果可用）
  if (typeof Worker !== 'undefined') {
    try {
      return await solveWithWorker(challenge.data, challenge.difficulty)
    } catch {
      // Worker 不可用，降级到主线程
    }
  }

  return solveInMainThread(challenge.data, challenge.difficulty)
}

function solveWithWorker(data: string, difficulty: number): Promise<number> {
  return new Promise((resolve, reject) => {
    const workerCode = `
      self.onmessage = async function(e) {
        const { data, difficulty } = e.data;
        const prefix = '0'.repeat(difficulty);
        let nonce = 0;
        while (nonce < 100000000) {
          const input = data + nonce;
          const encoded = new TextEncoder().encode(input);
          const hashBuffer = await crypto.subtle.digest('SHA-256', encoded);
          const hashArray = new Uint8Array(hashBuffer);
          let hashHex = '';
          for (const b of hashArray) hashHex += b.toString(16).padStart(2, '0');
          if (hashHex.startsWith(prefix)) {
            self.postMessage({ nonce });
            return;
          }
          nonce++;
        }
        self.postMessage({ error: 'exceeded max attempts' });
      };
    `
    const blob = new Blob([workerCode], { type: 'application/javascript' })
    const worker = new Worker(URL.createObjectURL(blob))

    const timeout = setTimeout(() => {
      worker.terminate()
      reject(new Error('PoW Worker timeout'))
    }, 30000)

    worker.onmessage = (e) => {
      clearTimeout(timeout)
      worker.terminate()
      if (e.data.error) reject(new Error(e.data.error))
      else resolve(e.data.nonce)
    }

    worker.onerror = () => {
      clearTimeout(timeout)
      worker.terminate()
      reject(new Error('PoW Worker error'))
    }

    worker.postMessage({ data, difficulty })
  })
}
