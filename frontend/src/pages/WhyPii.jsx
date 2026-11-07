import { Link } from "react-router-dom";

import "./Content.css";

export default function WhyPii() {
  return (
    <article className="content">
      <h1>Why personal information matters</h1>
      <p className="content__lead">
        Documents carry more about you than you think. Once a PDF is shared, you
        no longer control where it goes.
      </p>

      <section>
        <h2>What counts as personal information</h2>
        <p>
          Personal information (PII) is anything that points to a real person.
          Some of it is obvious, some is easy to forget:
        </p>
        <ul>
          <li>Government and tax IDs, such as Aadhaar and PAN numbers</li>
          <li>Passport, voter ID and driving licence numbers</li>
          <li>Bank account numbers, IFSC codes, UPI IDs and card numbers</li>
          <li>Phone numbers, email addresses and dates of birth</li>
          <li>Names, home addresses and vehicle registration numbers</li>
        </ul>
      </section>

      <section>
        <h2>What can go wrong</h2>
        <ul>
          <li>
            <strong>Fraud.</strong> A few identifiers are often enough to open
            accounts, apply for loans or take over a phone number in your name.
          </li>
          <li>
            <strong>Convincing scams.</strong> Scammers who know your real
            details sound like your bank or your employer, and people believe
            them.
          </li>
          <li>
            <strong>Unwanted exposure.</strong> A home address or phone number
            in a document that gets passed around can lead to harassment.
          </li>
          <li>
            <strong>No way back.</strong> Leaked identifiers cannot be changed
            like a password. Your date of birth stays your date of birth.
          </li>
        </ul>
      </section>

      <section>
        <h2>Why a black box is not enough</h2>
        <p>
          Many people hide details by drawing a black rectangle over them in a
          PDF viewer or editor. In many files this only adds a shape on top. The
          text underneath is still there, and anyone can select, copy or search
          it. Scanned documents can hide the same problem inside the image.
        </p>
        <p>
          Real redaction removes the content from the file itself. That is what
          SecurePDF does, and it checks the result before giving you the file.
        </p>
      </section>

      <section>
        <h2>Habits that help</h2>
        <ul>
          <li>Share only the pages and details the other person needs.</li>
          <li>Redact before you share, not after something goes wrong.</li>
          <li>
            Test the result: open the redacted file, try to select and copy the
            hidden area, and search for a number you covered.
          </li>
          <li>Keep the original somewhere private, and share only the copy.</li>
        </ul>
      </section>

      <section className="content__note">
        <p>
          See <Link to="/privacy">how we handle your data</Link> when you use
          SecurePDF.
        </p>
      </section>
    </article>
  );
}
