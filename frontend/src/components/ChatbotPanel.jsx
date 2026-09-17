import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Trash2, Cpu, Sparkles, Terminal, Activity } from 'lucide-react';

export default function ChatbotPanel({
  messages,
  onSendMessage,
  onClearChat,
  onOpenInspector,
  templates,
  selectedTemplate,
  setSelectedTemplate,
  loading,
  lastPipelineResult,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const examplePrompts = [
    'Show all customers',
    'Who spent the most money?',
    'List recent orders',
    'Generate sales insights',
    'Show customers from USA',
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handlePromptClick = (prompt) => {
    if (loading) return;
    onSendMessage(prompt);
  };

  // Basic markdown-like formatter for code blocks, bold, lists, and line breaks
  const formatContent = (text) => {
    if (!text) return '';
    // If text has code blocks:
    const parts = text.split(/(```[\s\S]*?```)/g);
    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const lines = part.slice(3, -3).trim().split('\n');
        const firstLine = lines[0].trim();
        const code = (firstLine.match(/^[a-z]+$/) ? lines.slice(1) : lines).join('\n');
        return (
          <pre key={index}>
            <code>{code}</code>
          </pre>
        );
      }

      // Format bold and newlines
      const lines = part.split('\n');
      return (
        <span key={index}>
          {lines.map((line, lineIdx) => {
            // Check bullet
            const isBullet = line.trim().startsWith('- ') || line.trim().startsWith('* ');
            const content = isBullet ? line.trim().slice(2) : line;

            // Simple bold parser
            const boldParts = content.split(/(\*\*.*?\*\*)/g).map((sub, sIdx) => {
              if (sub.startsWith('**') && sub.endsWith('**')) {
                return <strong key={sIdx}>{sub.slice(2, -2)}</strong>;
              }
              return sub;
            });

            return (
              <React.Fragment key={lineIdx}>
                {isBullet ? (
                  <div style={{ paddingLeft: '1rem', position: 'relative' }}>
                    <span style={{ position: 'absolute', left: '0.2rem' }}>•</span>
                    {boldParts}
                  </div>
                ) : (
                  <div>{boldParts}</div>
                )}
              </React.Fragment>
            );
          })}
        </span>
      );
    });
  };

  return (
    <div className="chat-container">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-title-group">
          <div className="chat-avatar">
            <Bot size={18} />
          </div>
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              MCP AI Assistant
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span className="status-dot" style={{ width: 5, height: 5 }}></span>
              <span>Tool-Augmented Model</span>
            </div>
          </div>
        </div>

        <div className="chat-header-actions">
          {/* Template Selector */}
          <select
            className="template-select"
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value)}
            title="AI Prompt Persona"
          >
            {templates.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>

          {/* AI Inspector Button */}
          <button
            className="btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            onClick={onOpenInspector}
            title="Inspect AI Execution Pipeline & MCP Tool Logs"
          >
            <Terminal size={13} color="var(--accent-cyan)" />
            <span>Inspector</span>
          </button>

          {/* Clear Button */}
          <button
            className="btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            onClick={onClearChat}
            title="Clear Chat Conversation"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="chat-messages-scroll">
        {messages.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--text-muted)',
              textAlign: 'center',
              padding: '2rem',
            }}
          >
            <div
              style={{
                width: 50,
                height: 50,
                borderRadius: '50%',
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1rem',
                color: 'var(--accent-primary)',
              }}
            >
              <Sparkles size={24} />
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
              How can I help you today?
            </h3>
            <p style={{ fontSize: '0.8rem', maxWidth: '320px', lineHeight: '1.5' }}>
              I can manage customers, place or track orders, analyze revenues, and query our live database through MCP tools.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-message-row ${msg.role}`}>
              {msg.role === 'assistant' && (
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    flexShrink: 0,
                    marginTop: '2px',
                  }}
                >
                  <Bot size={15} />
                </div>
              )}

              <div className="chat-bubble">
                {formatContent(msg.content)}
              </div>

              {msg.role === 'user' && (
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-secondary)',
                    flexShrink: 0,
                    marginTop: '2px',
                  }}
                >
                  <User size={15} />
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Spinner Indicator */}
        {loading && (
          <div className="chat-message-row assistant">
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                flexShrink: 0,
              }}
            >
              <Bot size={15} />
            </div>
            <div className="chat-bubble" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Activity size={16} className="spin" color="var(--accent-cyan)" />
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Executing MCP agent pipeline & tools...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Example Prompt Pills */}
      <div className="example-prompts-row">
        {examplePrompts.map((prompt, i) => (
          <button
            key={i}
            className="prompt-pill"
            onClick={() => handlePromptClick(prompt)}
            disabled={loading}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Input Bar */}
      <form onSubmit={handleSubmit} className="chat-input-container">
        <input
          type="text"
          className="chat-input"
          placeholder="Ask assistant or instruct an order..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={!input.trim() || loading}
          title="Send message"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
