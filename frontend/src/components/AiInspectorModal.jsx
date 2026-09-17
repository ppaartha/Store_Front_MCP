import React, { useState } from 'react';
import { X, CheckCircle2, Clock, Wrench, Brain, Layers, Cpu } from 'lucide-react';

export default function AiInspectorModal({ isOpen, onClose, pipelineResult, developerStatus }) {
  const [activeTab, setActiveTab] = useState('pipeline');

  if (!isOpen) return null;

  const timeline = pipelineResult?.timeline || [];
  const stages = pipelineResult?.stages || [];
  const toolRecords = pipelineResult?.tool_records || [];
  const memory = pipelineResult?.memory || {};
  const usage = pipelineResult?.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
  const catalog = developerStatus?.catalog || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: 780 }} onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Cpu size={18} color="var(--accent-cyan)" />
            <h3 className="modal-title">AI Pipeline & MCP Tool Inspector</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Modal Tab Switcher */}
        <div style={{ display: 'flex', gap: '0.5rem', padding: '0.75rem 1.5rem', borderBottom: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)' }}>
          <button
            className={`prompt-pill ${activeTab === 'pipeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('pipeline')}
          >
            Pipeline Stages ({stages.length})
          </button>
          <button
            className={`prompt-pill ${activeTab === 'tools' ? 'active' : ''}`}
            onClick={() => setActiveTab('tools')}
          >
            MCP Tool Calls ({toolRecords.length})
          </button>
          <button
            className={`prompt-pill ${activeTab === 'agents' ? 'active' : ''}`}
            onClick={() => setActiveTab('agents')}
          >
            Specialist Agents ({catalog.length})
          </button>
          <button
            className={`prompt-pill ${activeTab === 'memory' ? 'active' : ''}`}
            onClick={() => setActiveTab('memory')}
          >
            Memory & Tokens
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {activeTab === 'pipeline' && (
            <div>
              {/* Timeline */}
              {timeline.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.75rem' }}>
                    Execution Sequence
                  </h4>
                  <div className="pipeline-timeline">
                    {timeline.map((step, idx) => (
                      <div key={idx} className="timeline-step">
                        <div className="timeline-bullet">✓</div>
                        <div className="timeline-text">{step}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Stages Accordion */}
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                Stage Payloads
              </h4>
              {stages.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No pipeline stages recorded yet. Send a chat message to inspect execution traces.
                </div>
              ) : (
                stages.map((stage, idx) => (
                  <div key={idx} className="stage-card">
                    <div className="stage-card-header">
                      <span>{stage.name}</span>
                    </div>
                    <pre className="stage-card-body">
                      {JSON.stringify(stage.payload, null, 2)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'tools' && (
            <div>
              {toolRecords.length === 0 ? (
                <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No MCP tools invoked during the last conversation turn.
                </div>
              ) : (
                toolRecords.map((t, idx) => (
                  <div key={idx} className="stage-card">
                    <div className="stage-card-header" style={{ color: t.success ? '#34d399' : '#fb7185' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Wrench size={13} />
                        <span>{t.tool_name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        <Clock size={11} />
                        <span>{t.duration_ms ? `${t.duration_ms.toFixed(1)}ms` : 'Completed'}</span>
                      </div>
                    </div>
                    <div className="stage-card-body">
                      <div style={{ color: 'var(--accent-primary)', marginBottom: '0.3rem', fontWeight: 600 }}>Arguments:</div>
                      {JSON.stringify(t.arguments, null, 2)}
                      <div style={{ color: '#34d399', margin: '0.5rem 0 0.3rem 0', fontWeight: 600 }}>Result:</div>
                      {JSON.stringify(t.result, null, 2)}
                      {t.error && (
                        <div style={{ color: '#fb7185', marginTop: '0.5rem' }}>
                          Error: {t.error}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'agents' && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.75rem' }}>
                {catalog.map((agent, i) => (
                  <div key={i} className="stage-card" style={{ padding: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                      <Brain size={16} color="var(--accent-cyan)" />
                      <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{agent.name}</span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                      {agent.description}
                    </p>
                    {agent.capabilities && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                        {agent.capabilities.map((cap, cIdx) => (
                          <span
                            key={cIdx}
                            className="badge badge-active"
                            style={{ fontSize: '0.68rem', background: 'rgba(99,102,241,0.1)', color: '#818cf8', borderColor: 'rgba(99,102,241,0.2)' }}
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'memory' && (
            <div>
              {/* Token Usage */}
              <div className="kpi-grid" style={{ marginBottom: '1.25rem' }}>
                <div className="kpi-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="kpi-header"><span>Prompt Tokens</span></div>
                  <div className="kpi-value" style={{ fontSize: '1.25rem' }}>{usage.prompt_tokens}</div>
                </div>
                <div className="kpi-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="kpi-header"><span>Completion Tokens</span></div>
                  <div className="kpi-value" style={{ fontSize: '1.25rem' }}>{usage.completion_tokens}</div>
                </div>
                <div className="kpi-card" style={{ padding: '0.75rem 1rem' }}>
                  <div className="kpi-header"><span>Total Tokens</span></div>
                  <div className="kpi-value" style={{ fontSize: '1.25rem', color: 'var(--accent-emerald)' }}>
                    {usage.total_tokens}
                  </div>
                </div>
              </div>

              <div className="stage-card">
                <div className="stage-card-header">
                  <span>Current Conversation Memory Snapshot</span>
                </div>
                <pre className="stage-card-body">
                  {JSON.stringify(memory, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
