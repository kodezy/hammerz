export type WsMessage = {
  type: string
  auction_id?: string
  version?: number
  snapshot?: Record<string, unknown>
  bid?: Record<string, unknown>
  server_time?: string
}

export type LotSocket = {
  close: () => void
}

export function connectLotSocket(
  auctionId: string,
  onMessage: (msg: WsMessage) => void,
  onGap: () => void,
  onConnected?: (connected: boolean) => void,
): LotSocket {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${window.location.host}/ws/auctions/${auctionId}`
  let closed = false
  let backoff = 1000
  let socket: WebSocket | null = null
  let lastVersion = 0
  let pollTimer: number | undefined

  const poll = () => {
    pollTimer = window.setInterval(() => onGap(), 5000)
  }

  const connect = () => {
    if (closed) return
    socket = new WebSocket(url)
    socket.onopen = () => {
      backoff = 1000
      onConnected?.(true)
      poll()
    }
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WsMessage
        if (msg.version !== undefined) {
          if (msg.version <= lastVersion) return
          if (msg.version > lastVersion + 1) {
            onGap()
            return
          }
          lastVersion = msg.version
        }
        onMessage(msg)
      } catch {
        /* ignore */
      }
    }
    socket.onclose = () => {
      onConnected?.(false)
      if (pollTimer) window.clearInterval(pollTimer)
      if (!closed) {
        window.setTimeout(connect, backoff)
        backoff = Math.min(backoff * 2, 15000)
      }
    }
  }

  connect()

  return {
    close: () => {
      closed = true
      if (pollTimer) window.clearInterval(pollTimer)
      socket?.close()
    },
  }
}
