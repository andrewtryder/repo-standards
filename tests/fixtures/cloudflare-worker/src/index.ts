export function greet(name = "world"): string {
  return `hello ${name}`;
}

export default {
  async fetch(): Promise<Response> {
    return new Response(greet("worker"), { status: 200 });
  },
};
