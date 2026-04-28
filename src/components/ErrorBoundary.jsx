import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 p-8 text-center">
          <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center text-2xl">
            warning
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground mb-1">Something went wrong</h2>
            <p className="text-sm text-muted-foreground max-w-md">
              An unexpected error occurred. Your data is safe. Click below to reload.
            </p>
          </div>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Reload Page
          </button>
          {this.state.error && (
            <p className="text-[11px] text-muted-foreground/60 font-mono max-w-sm break-all">
              {this.state.error.message}
            </p>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}