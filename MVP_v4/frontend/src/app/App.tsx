import { useEffect, useState } from 'react';
import { getHealth } from '../api/health';

export function App() {
  const [connection, setConnection] = useState('연결 확인 중');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setConnection('연결 확인 중');
    getHealth(controller.signal)
      .then(() => { if (!controller.signal.aborted) setConnection('서버 연결됨'); })
      .catch(() => { if (!controller.signal.aborted) setConnection('서버 연결을 확인해 주세요'); });
    return () => controller.abort();
  }, [attempt]);

  return (
    <div className="workspace">
      <header className="header">
        <a className="brand" href="/" aria-label="CSR 홈">CSR<span>Case Share Room</span></a>
        <span className="environment">개발 미리보기</span>
      </header>
      <main>
        <section className="welcome" aria-labelledby="welcome-title">
          <span className="eyebrow">함께 확인하고, 안전하게 대응합니다</span>
          <h1 id="welcome-title">하나의 사건에서<br />고객과 은행을 연결합니다.</h1>
          <p>상황을 이해하고 필요한 사실을 확인하는 상담 공간을 준비하고 있습니다.</p>
          <div className="notice">
            <h2>상담 기능 준비 중</h2>
            <p>현재는 연결 상태를 확인할 수 있습니다. 사건 생성과 상담은 아직 제공되지 않습니다.</p>
          </div>
        </section>
        <aside className="connection" aria-labelledby="connection-title">
          <h2 id="connection-title">연결 상태</h2>
          <p role="status">{connection}</p>
          <button type="button" onClick={() => setAttempt((value) => value + 1)}>다시 확인</button>
        </aside>
      </main>
      <footer>CSR · Case Share Room</footer>
    </div>
  );
}
