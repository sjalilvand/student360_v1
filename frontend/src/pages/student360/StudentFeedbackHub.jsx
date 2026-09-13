// Student 360 - Feedback hub: vote / rate / propose (merged feature, student-facing).
import { useState } from "react";
import VoteForm from "../VoteForm";
import RatingForm from "../RatingForm";
import ProposalForm from "../ProposalForm";
import { Card } from "./shared";

export default function StudentFeedbackHub() {
  const [tab, setTab] = useState("vote");

  return (
    <div className="s360-page">
      <h2>🗳 نظرسنجی و بازخورد دروس</h2>

      <div className="s360-tabs-row">
        <button className={tab === "vote" ? "active" : ""}
                onClick={() => setTab("vote")}>👍 رأی و درخواست درس</button>
        <button className={tab === "rating" ? "active" : ""}
                onClick={() => setTab("rating")}>⭐ امتیازدهی به کلاس‌ها</button>
        <button className={tab === "proposal" ? "active" : ""}
                onClick={() => setTab("proposal")}>💡 پیشنهاد درس جدید</button>
      </div>

      {tab === "vote" && <VoteForm />}
      {tab === "rating" && <RatingForm />}
      {tab === "proposal" && <ProposalForm />}
    </div>
  );
}
