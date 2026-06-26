import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { FileText, Shield, Activity, Copy, Check, Search, ArrowRight } from 'lucide-react'

const API_BASE = ''

export default function Dashboard({ setActivePanel, onSelectFile }) {
  const [health, setHealth] = useState(null)
  const [files, setFiles] = useState([])
  const [states, setStates] = useState({})
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      const [hRes, fRes] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/files`),
      ])
      const h = await hRes.json()
      const f = await fRes.json()
      setHealth(h)
      const fileList = f.files || []
      setFiles(fileList)

      // Fetch superposition state for each file
      const statePromises = fileList.map(async (file) => {
        try {
          const sRes = await fetch(`${API_BASE}/superpose/state/${file.file_id}`)
          return [file.file_id, await sRes.json()]
        } catch {
          return [file.file_id, { error: true }]
        }
      })
      const stateEntries = await Promise.all(statePromises)
      setStates(Object.fromEntries(stateEntries))
    } catch {
      setHealth({ status: 'error' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, 15000)
    return () => clearInterval(id)
  }, [fetchAll])

  const copyUrl = (fileId) => {
    navigator.clipboard?.writeText(`${API_BASE}/meta/${fileId}`)
    setCopied(fileId)
    setTimeout(() => setCopied(null), 2000)
  }

  const isLive = health?.status === 'ok'

  // Compute real aggregate stats
  const totalQueries = Object.values(states).reduce((sum, s) => sum + (s?.total_queries || 0), 0)
  const totalIndexBytes = Object.values(states).reduce((sum, s) => sum + (s?.index_size_bytes || 0), 0)
  const liveCount = Object.values(states).filter(s => s?.session_status === 'live').length
  const indexKB = (totalIndexBytes / 1024).toFixed(1)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <motion.div
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="text-sm text-secondary font-mono"
        >
          Connecting to Space...
        </motion.div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4 h-full overflow-y-auto thin-scrollbar">
      {/* Real status banner */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-success animate-pulse' : 'bg-critical'}`} />
            <span className="text-sm font-semibold">Space Status</span>
          </div>
          <span className={`text-xs font-mono ${isLive ? 'text-success' : 'text-critical'}`}>
            {isLive ? '● VERIFIED' : '● ERROR'}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-secondary mb-1">Files</div>
            <div className="text-xl font-bold tabular-nums">{files.length} indexed</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-secondary mb-1">Live Sessions</div>
            <div className="text-xl font-bold tabular-nums text-success">{liveCount}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-secondary mb-1">Queries Served</div>
            <div className="text-xl font-bold tabular-nums">{totalQueries}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-secondary mb-1">Index Size</div>
            <div className="text-xl font-bold tabular-nums">{indexKB} KB</div>
          </div>
        </div>
      </motion.div>

      {/* Real file list */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary" />
            <span className="text-sm font-semibold">Indexed Files</span>
          </div>
          <button
            onClick={() => setActivePanel('query')}
            className="flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors"
          >
            <Search className="w-3 h-3" />
            Query
          </button>
        </div>

        {files.length === 0 ? (
          <div className="text-center py-8 text-secondary text-sm">
            No files indexed. Upload via the API.
          </div>
        ) : (
          <div className="space-y-2">
            {files.map((file, i) => {
              const state = states[file.file_id]
              const isFileLive = state?.session_status === 'live'
              const queries = state?.total_queries || 0
              const idxSize = state?.index_size_bytes ? `${(state.index_size_bytes / 1024).toFixed(1)} KB` : '—'
              const origSize = state?.original_size || file.size

              return (
                <motion.div
                  key={file.file_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  className="flex items-center gap-4 py-3 px-3 rounded-xl hover:bg-white/5 transition-all group cursor-pointer"
                  onClick={() => onSelectFile(file.file_id)}
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isFileLive ? 'bg-success animate-pulse' : 'bg-secondary'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{file.filename}</span>
                      <span className="text-[10px] text-secondary font-mono">{file.file_id}</span>
                    </div>
                    <div className="text-[10px] text-secondary mt-0.5">
                      {origSize} → {idxSize} index · {queries} queries
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); copyUrl(file.file_id) }}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] glass hover:glass-orange transition-all opacity-0 group-hover:opacity-100"
                  >
                    {copied === file.file_id ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                    {copied === file.file_id ? 'Copied' : 'Copy URL'}
                  </button>
                  <ArrowRight className="w-3 h-3 text-secondary/40 group-hover:text-primary transition-colors" />
                </motion.div>
              )
            })}
          </div>
        )}
      </motion.div>

      {/* Real endpoints reference */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-2xl p-5"
      >
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Live Endpoints</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-[10px] font-mono">
          {[
            ['GET', '/health'],
            ['GET', '/files'],
            ['GET', '/meta/{id}'],
            ['GET', '/summary/{id}'],
            ['GET', '/search/{id}?q='],
            ['GET', '/chunk/{id}/{idx}'],
            ['GET', '/capabilities/{id}'],
            ['GET', '/stats/{id}'],
            ['GET', '/superpose/state/{id}'],
            ['POST', '/query/sql/{id}'],
          ].map(([method, path]) => (
            <div key={path} className="flex items-center gap-2 py-1.5 px-2 rounded-lg bg-white/3">
              <span className={method === 'GET' ? 'text-success' : 'text-primary'}>{method}</span>
              <span className="text-secondary truncate">{path}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
