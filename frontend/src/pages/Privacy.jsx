import { Link } from "react-router-dom";

import "./Content.css";

export default function Privacy() {
  return (
    <article className="content">
      <h1>How we handle your data</h1>
      <p className="content__lead">
        SecurePDF is built to keep as little of your information as possible,
        for as short a time as possible.
      </p>

      <section>
        <h2>Your documents</h2>
        <ul>
          <li>
            Every uploaded file is encrypted before it is stored. Each document
            has its own encryption key.
          </li>
          <li>
            We never store your file name, and we never store the sensitive text
            we find. We keep only what type of item was found and where it is on
            the page.
          </li>
          <li>
            Files are deleted automatically after a short time (12 hours by
            default). You can also delete a document yourself at any time.
          </li>
          <li>
            When a document is deleted, its encryption keys are erased first, so
            anything left behind can no longer be read.
          </li>
          <li>
            Detection and text recognition run on our own server. We do not send
            your documents to outside AI or OCR services.
          </li>
        </ul>
      </section>

      <section>
        <h2>Your redacted file</h2>
        <ul>
          <li>
            Redaction removes the text and image content from the file instead
            of covering it, and clears hidden metadata.
          </li>
          <li>
            After redacting, we check the new file. If any content is still
            readable under a redacted area, we do not give you the file.
          </li>
          <li>
            Only your account can open your documents and download your results.
          </li>
        </ul>
      </section>

      <section>
        <h2>Your account</h2>
        <ul>
          <li>
            We keep your email address and a secure hash of your password.
          </li>
          <li>We never store your password itself.</li>
          <li>
            We keep a simple record of actions, such as downloading a file or
            choosing to keep a sensitive item visible. It holds no document
            content.
          </li>
        </ul>
      </section>

      <section>
        <h2>What SecurePDF cannot promise</h2>
        <ul>
          <li>
            Detection is never perfect. It may miss an item or flag the wrong
            one, so review every page before you share a file.
          </li>
          <li>
            Today we detect structured details such as ID numbers, bank details,
            phone numbers and email addresses. Names and addresses are not found
            automatically yet, so use <strong>Add a box</strong> on the review
            page to cover them.
          </li>
          <li>
            While a scanned page is being read, the server may briefly keep a
            temporary image of it. We are working to remove that.
          </li>
        </ul>
      </section>

      <section className="content__note">
        <p>
          New to this? Read{" "}
          <Link to="/why-pii">why personal information matters</Link>.
        </p>
      </section>
    </article>
  );
}
