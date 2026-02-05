import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowRight, GitBranch, Layers, Zap, Radio, FileCode, BookOpen } from "lucide-react"
import Link from "next/link"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Zap className="h-6 w-6 text-primary" />
            <span className="text-xl font-semibold">MCP-Flow</span>
          </div>
          <nav className="flex items-center gap-6">
            <Link href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Features
            </Link>
            <Link href="#quickstart" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Quick Start
            </Link>
            <Link
              href="https://github.com/copyleftdev/mcp-flow"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              GitHub
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-24 text-center">
        <div className="mx-auto max-w-3xl space-y-6">
          <div className="flex justify-center gap-2">
            <Badge variant="secondary" className="font-mono">
              v0.1
            </Badge>
            <Badge variant="outline" className="font-mono">
              MIT License
            </Badge>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl text-balance">
            WebTransport Binding for{" "}
            <span className="text-primary">Model Context Protocol</span>
          </h1>
          <p className="text-lg text-muted-foreground text-balance leading-relaxed">
            MCP-Flow eliminates head-of-line blocking in MCP by leveraging QUIC streams and datagrams 
            for parallel, mixed-reliability communication.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4">
            <Button size="lg" asChild>
              <Link href="https://github.com/copyleftdev/mcp-flow" target="_blank" rel="noopener noreferrer">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#features">
                Learn More
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section className="border-y border-border/40 bg-muted/30 py-16">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-4xl">
            <h2 className="text-2xl font-semibold text-center mb-8">Why MCP-Flow?</h2>
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="border-destructive/30 bg-destructive/5">
                <CardHeader>
                  <CardTitle className="text-lg">Traditional MCP</CardTitle>
                  <CardDescription>Single-threaded limitations</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-destructive">×</span>
                    <span>Single stream blocks all messages</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-destructive">×</span>
                    <span>Large responses freeze the connection</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-destructive">×</span>
                    <span>No progress updates during transfers</span>
                  </div>
                </CardContent>
              </Card>
              <Card className="border-primary/30 bg-primary/5">
                <CardHeader>
                  <CardTitle className="text-lg">MCP-Flow</CardTitle>
                  <CardDescription>Parallel, efficient streaming</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-primary">✓</span>
                    <span>Parallel streams for concurrent operations</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-primary">✓</span>
                    <span>Bulk data flows on dedicated Execution Streams</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-primary">✓</span>
                    <span>Real-time datagrams for progress, audio, logs</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-4 py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-3xl font-bold text-center mb-4">Key Features</h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            Built on modern web standards for maximum performance and reliability
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader>
                <Layers className="h-10 w-10 text-primary mb-2" />
                <CardTitle className="text-lg">No Head-of-Line Blocking</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Large responses stream independently without blocking other messages.
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <Radio className="h-10 w-10 text-primary mb-2" />
                <CardTitle className="text-lg">Mixed Reliability</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Datagrams for progress and audio, reliable streams for critical data.
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <FileCode className="h-10 w-10 text-primary mb-2" />
                <CardTitle className="text-lg">Encoding Negotiation</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                JSON or CBOR encoding, negotiated automatically at connection time.
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <GitBranch className="h-10 w-10 text-primary mb-2" />
                <CardTitle className="text-lg">Backward Compatible</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Standard MCP JSON-RPC messages work seamlessly with the new transport.
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Quick Start Section */}
      <section id="quickstart" className="border-t border-border/40 bg-muted/30 py-24">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-3xl font-bold text-center mb-4">Quick Start</h2>
            <p className="text-center text-muted-foreground mb-8">
              Get up and running in seconds
            </p>
            <Card>
              <CardContent className="p-6">
                <pre className="bg-background rounded-lg p-4 overflow-x-auto text-sm font-mono">
                  <code>{`# Build everything
make build

# Terminal 1: Start a server
make run-go

# Terminal 2: Run the test client
./bin/mcp-flow-client`}</code>
                </pre>
              </CardContent>
            </Card>
            <div className="mt-8 grid sm:grid-cols-3 gap-4">
              <Card className="text-center">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Go</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge variant="secondary" className="font-mono">1.21+</Badge>
                </CardContent>
              </Card>
              <Card className="text-center">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Python</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge variant="secondary" className="font-mono">3.11+</Badge>
                </CardContent>
              </Card>
              <Card className="text-center">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">TypeScript</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge variant="secondary" className="font-mono">Deno</Badge>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Documentation Section */}
      <section className="container mx-auto px-4 py-24">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-3xl font-bold text-center mb-4">Documentation</h2>
          <p className="text-center text-muted-foreground mb-12">
            Everything you need to integrate MCP-Flow
          </p>
          <div className="grid sm:grid-cols-2 gap-6">
            <Link href="https://github.com/copyleftdev/mcp-flow/blob/main/schema/0.1/IMPLEMENTATION.md" target="_blank" rel="noopener noreferrer">
              <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader>
                  <BookOpen className="h-8 w-8 text-accent mb-2" />
                  <CardTitle>Implementation Guide</CardTitle>
                  <CardDescription>Wire formats, state machine, error codes</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link href="https://github.com/copyleftdev/mcp-flow/blob/main/schema/0.1/README.md" target="_blank" rel="noopener noreferrer">
              <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader>
                  <FileCode className="h-8 w-8 text-accent mb-2" />
                  <CardTitle>Schema Reference</CardTitle>
                  <CardDescription>Type definitions and constants</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link href="https://github.com/copyleftdev/mcp-flow/blob/main/examples/README.md" target="_blank" rel="noopener noreferrer">
              <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader>
                  <Layers className="h-8 w-8 text-accent mb-2" />
                  <CardTitle>Examples</CardTitle>
                  <CardDescription>Running the reference servers</CardDescription>
                </CardHeader>
              </Card>
            </Link>
            <Link href="https://github.com/copyleftdev/mcp-flow/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener noreferrer">
              <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader>
                  <GitBranch className="h-8 w-8 text-accent mb-2" />
                  <CardTitle>Contributing</CardTitle>
                  <CardDescription>How to contribute to the project</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>
            MCP-Flow is open source under the{" "}
            <Link 
              href="https://github.com/copyleftdev/mcp-flow/blob/main/LICENSE" 
              target="_blank" 
              rel="noopener noreferrer"
              className="underline underline-offset-4 hover:text-foreground"
            >
              MIT License
            </Link>
          </p>
        </div>
      </footer>
    </div>
  )
}
