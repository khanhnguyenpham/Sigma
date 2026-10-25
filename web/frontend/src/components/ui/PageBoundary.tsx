import { Component, type ReactNode } from "react";
export class PageBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <section className="empty error-page" role="alert">
        <h2>Không thể hiển thị màn hình này</h2>
        <p>Hãy thử mở lại màn hình. Các phương án đã có không bị thay đổi.</p>
        <button
          className="primary"
          onClick={() => this.setState({ failed: false })}
        >
          Thử mở lại
        </button>
        <button className="secondary" onClick={() => window.location.reload()}>
          Tải lại trang
        </button>

      </section>
    ) : (
      this.props.children
    );
  }
}
