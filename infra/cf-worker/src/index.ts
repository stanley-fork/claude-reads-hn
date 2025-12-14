interface Env {
  GITHUB_TOKEN: string;
  GITHUB_REPO: string;
  WORKFLOW_FILE: string;
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    const url = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}/dispatches`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "claude-reads-hn-trigger",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ref: "main",
        inputs: {
          story_count: "20"
        }
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      console.error(`Failed to trigger workflow: ${response.status} ${text}`);
      throw new Error(`GitHub API error: ${response.status}`);
    }

    console.log(`Triggered ${env.WORKFLOW_FILE} at ${new Date().toISOString()}`);
  },

  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/trigger" && request.method === "POST") {
      // Manual trigger endpoint (optional, for testing)
      await this.scheduled({} as ScheduledEvent, env, ctx);
      return new Response("Workflow triggered", { status: 200 });
    }

    if (url.pathname === "/health") {
      return new Response("ok", { status: 200 });
    }

    return new Response("claude-reads-hn trigger worker", { status: 200 });
  },
};
