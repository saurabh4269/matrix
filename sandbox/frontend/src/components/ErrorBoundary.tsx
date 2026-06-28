import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  label?: string
  onBack?: () => void
}

interface State {
  err: Error | null
  info: string | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { err: null, info: null }

  static getDerivedStateFromError(err: Error): State {
    return { err, info: null }
  }

  componentDidCatch(err: Error, info: { componentStack: string }) {
    // Surface in the dev console too.
    console.error('ErrorBoundary caught', this.props.label, err, info.componentStack)
    this.setState({ err, info: info.componentStack })
  }

  reset = () => this.setState({ err: null, info: null })

  render() {
    if (this.state.err) {
      return (
        <section className="min-h-screen w-full px-6 sm:px-10 py-8 bg-canvas text-ink">
          <h2 className="font-serif text-display text-signal-concern">
            Something broke in this view.
          </h2>
          <p className="mt-3 font-serif text-title text-ink-secondary max-w-[60ch]">
            {this.props.label ?? 'View'} hit a runtime error. The rest of the app is
            still healthy; you can go back to the deck.
          </p>
          <pre className="mt-6 p-4 bg-card border border-hairline rounded font-mono text-small text-signal-concern whitespace-pre-wrap overflow-x-auto">
            {this.state.err.name}: {this.state.err.message}
          </pre>
          {this.state.info && (
            <details className="mt-3">
              <summary className="font-sans text-small text-ink-tertiary cursor-pointer">
                Component stack
              </summary>
              <pre className="mt-2 p-4 bg-card border border-hairline rounded font-mono text-small text-ink-tertiary whitespace-pre-wrap overflow-x-auto">
                {this.state.info}
              </pre>
            </details>
          )}
          <div className="mt-6 flex gap-4">
            <button
              onClick={this.reset}
              className="font-sans text-body bg-action text-canvas px-6 py-3 rounded-full hover:bg-ink transition"
            >
              Retry
            </button>
            {this.props.onBack && (
              <button
                onClick={this.props.onBack}
                className="font-sans text-body text-ink-secondary hover:text-ink transition"
              >
                Back to deck
              </button>
            )}
          </div>
        </section>
      )
    }
    return this.props.children
  }
}
