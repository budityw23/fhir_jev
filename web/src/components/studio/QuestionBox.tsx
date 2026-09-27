export interface QuestionBoxProps { questions: string[]; }

/** Show the literal decision question sent to Jev. */
export function QuestionBox({ questions }: QuestionBoxProps) {
  return (
    <section className="question-box">
      <h3>What Jev sees</h3>
      {questions.map((question) => <p key={question}>{question}</p>)}
    </section>
  );
}
