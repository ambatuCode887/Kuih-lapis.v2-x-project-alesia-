import { useEffect, useState } from 'react';
import './download-warning.css';

const REVIEW_PREFIX = 'download-review-';

interface DownloadReview {
  downloadId: number;
  filename: string;
  domain: string;
  status: 'malicious' | 'unknown';
  details: string;
}

interface ActionResponse {
  ok: boolean;
  error?: string;
}

function isDownloadReview(value: unknown): value is DownloadReview {
  if (!value || typeof value !== 'object') return false;
  const review = value as Record<string, unknown>;
  return (
    typeof review.downloadId === 'number' &&
    typeof review.filename === 'string' &&
    typeof review.domain === 'string' &&
    (review.status === 'malicious' || review.status === 'unknown') &&
    typeof review.details === 'string'
  );
}

export default function DownloadWarning() {
  const [reviews, setReviews] = useState<DownloadReview[]>([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    const loadReviews = async () => {
      const stored = await browser.storage.local.get(null);
      const pending = Object.entries(stored)
        .filter(
          ([key, value]) =>
            key.startsWith(REVIEW_PREFIX) && isDownloadReview(value),
        )
        .map(([, value]) => value as DownloadReview);
      setReviews(pending);
      setError('');
    };

    void loadReviews().catch((cause: unknown) => {
      setError(
        cause instanceof Error
          ? cause.message
          : 'Pending download warnings could not be loaded.',
      );
    });

    const onChange = (
      changes: Record<string, { newValue?: unknown }>,
      area: string,
    ) => {
      if (
        area === 'local' &&
        Object.keys(changes).some((key) => key.startsWith(REVIEW_PREFIX))
      ) {
        void loadReviews().catch((cause: unknown) => {
          setError(
            cause instanceof Error
              ? cause.message
              : 'Pending download warnings could not be updated.',
          );
        });
      }
    };
    browser.storage.onChanged.addListener(onChange);
    void browser.action.setBadgeText({ text: '' });
    return () => browser.storage.onChanged.removeListener(onChange);
  }, []);

  async function choose(downloadId: number, action: 'proceed' | 'cancel') {
    if (busyId !== null) return;
    setBusyId(downloadId);
    setError('');
    try {
      const response = (await browser.runtime.sendMessage({
        type: 'download-review-action',
        downloadId,
        action,
      })) as ActionResponse;
      if (!response?.ok) {
        setError(response?.error ?? 'The download could not be updated.');
        return;
      }
      setReviews((current) =>
        current.filter((review) => review.downloadId !== downloadId),
      );
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'The download could not be updated.',
      );
    } finally {
      setBusyId(null);
    }
  }

  if (reviews.length === 0 && !error) return null;

  return (
    <div className="download-warning-overlay">
      {error && <p className="warning__error" role="alert">{error}</p>}
      {reviews.map((review) => {
        const malicious = review.status === 'malicious';
        const busy = busyId === review.downloadId;
        return (
          <section
            key={review.downloadId}
            className={`warning ${malicious ? 'warning--danger' : ''}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={`download-warning-title-${review.downloadId}`}
          >
            <div className="warning__badge" aria-hidden="true">
              {malicious ? '!' : '?'}
            </div>
            <p className="warning__eyebrow">Cyber Assistant · Download check</p>
            <h1 id={`download-warning-title-${review.downloadId}`}>
              {malicious
                ? 'This file may be malicious'
                : 'This download could not be verified'}
            </h1>
            <p className="warning__file">{review.filename}</p>
            {review.domain && (
              <p className="warning__domain">Source domain: {review.domain}</p>
            )}
            <p className="warning__details">{review.details}</p>
            <p className="warning__caveat">
              This check evaluates the source domain only; the downloaded file’s
              contents have not been scanned.
            </p>
            <div className="warning__actions">
              <button
                className="warning__cancel"
                disabled={busy}
                onClick={() => choose(review.downloadId, 'cancel')}
                type="button"
              >
                Cancel download
              </button>
              <button
                className="warning__proceed"
                disabled={busy}
                onClick={() => choose(review.downloadId, 'proceed')}
                type="button"
              >
                {busy ? 'Please wait…' : 'Download anyway'}
              </button>
            </div>
            {error && <p className="warning__error" role="alert">{error}</p>}
          </section>
        );
      })}
    </div>
  );
}
