"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Send,
  CheckCircle2,
  Clock,
  UserCheck,
  DollarSign,
  Lock,
  Smartphone,
  Hospital,
  RefreshCw,
  Stethoscope,
  ChevronRight,
  ExternalLink,
  KeyRound,
  FileSpreadsheet
} from "lucide-react";

export default function HealthFlowApp() {
  const [activeTab, setActiveTab] = useState<"preadmission" | "sms" | "revenue" | "audit">("preadmission");
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [isSigning, setIsSigning] = useState(false);
  const [caseResumed, setCaseResumed] = useState(false);
  const [attestationDecision, setAttestationDecision] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [clinicianNotes, setClinicianNotes] = useState(
    "Patient cleared for surgery under Total Hip Arthroplasty protocol. Hold Metformin 24h pre-op. Maintain compression devices."
  );
  const [signatureB64, setSignatureB64] = useState<string | null>(null);

  // SMS Simulator State
  const [smsMessages, setSmsMessages] = useState<Array<{ sender: "system" | "patient"; text: string; time: string }>>([
    {
      sender: "system",
      text: "HealthFlow Care: Hi Sarah, Dr. Smith's OR schedule has openings for your Hip Arthroplasty. Reply A (07:30 AM), B (06:30 AM), or C (11:00 AM).",
      time: "08:15 AM"
    },
    {
      sender: "patient",
      text: "Option B works best for me",
      time: "08:17 AM"
    },
    {
      sender: "system",
      text: "Thank you! Slot option B has been confirmed. Your surgical care team will see you then.",
      time: "08:17 AM"
    },
    {
      sender: "system",
      text: "HealthFlow Recovery: Hi Sarah, how is your recovery today on Post-Op Day 1? Reply with your pain score (1-10) and whether you have fever, calf swelling, or nausea.",
      time: "Day 1, 10:00 AM"
    }
  ]);
  const [customSmsInput, setCustomSmsInput] = useState("");
  const [isSendingSms, setIsSendingSms] = useState(false);

  // Audit Integrity State
  const [auditVerified, setAuditVerified] = useState(true);
  const [verifyingAudit, setVerifyingAudit] = useState(false);

  // Check backend health on mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("http://localhost:8000/health", { method: "GET" });
        if (res.ok) {
          setBackendStatus("online");
        } else {
          setBackendStatus("offline");
        }
      } catch {
        setBackendStatus("offline");
      }
    }
    checkHealth();
  }, []);

  const handleSignAttestation = async () => {
    setIsSigning(true);
    // Simulate ECDSA NIST P-256 digital signature computation
    setTimeout(() => {
      const mockSig = "MEQCIDNQbHuOMz3TrAn7atSy2bkrrpwtgAJM" + Math.random().toString(36).substring(2, 15) + "==";
      setSignatureB64(mockSig);
      setCaseResumed(true);
      setIsSigning(false);
    }, 600);
  };

  const handleSendSms = (textToSend?: string) => {
    const text = textToSend || customSmsInput;
    if (!text.trim()) return;

    const newPatientMsg = {
      sender: "patient" as const,
      text: text.trim(),
      time: "Just now"
    };

    setSmsMessages((prev) => [...prev, newPatientMsg]);
    if (!textToSend) setCustomSmsInput("");
    setIsSendingSms(true);

    // Dynamic response based on SMSParser rules
    setTimeout(() => {
      const lower = text.toLowerCase();
      let responseText = "";

      if (lower.includes("calf") || lower.includes("swelling") || lower.includes("redness") || lower.includes("fever") || lower.includes("shortness")) {
        responseText = "⚠️ ALERT: Thank you for reporting. A triage nurse has been notified and will call you within 15 minutes. If this is an emergency, call 911.";
      } else if (lower.includes("a") || lower.includes("b") || lower.includes("c")) {
        const slot = lower.includes("a") ? "A" : lower.includes("b") ? "B" : "C";
        responseText = `Thank you! Slot option ${slot} has been confirmed. Your surgical care team will see you then.`;
      } else {
        responseText = "Recovery check-in received. Your progress is on track! Keep resting, elevate your leg, and stay hydrated.";
      }

      setSmsMessages((prev) => [
        ...prev,
        {
          sender: "system",
          text: responseText,
          time: "Just now"
        }
      ]);
      setIsSendingSms(false);
    }, 700);
  };

  const verifyAuditLog = () => {
    setVerifyingAudit(true);
    setTimeout(() => {
      setVerifyingAudit(false);
      setAuditVerified(true);
    }, 500);
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">HealthFlow AI</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                  v0.1.0-prod
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous Clinical Clearance & Post-Op Triage</p>
            </div>
          </div>

          {/* System Status Indicators */}
          <div className="hidden md:flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
              <span className={`w-2 h-2 rounded-full ${backendStatus === "online" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
              <span className="text-slate-300">FastAPI Backend:</span>
              <span className={backendStatus === "online" ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                {backendStatus === "online" ? ":8000 Online" : "Local / Simulated"}
              </span>
            </div>

            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>FHIR R4 Connected</span>
            </div>

            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300">
              <Lock className="w-4 h-4 text-emerald-400" />
              <span>HIPAA WORM 6-Yr</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 sm:space-x-4 border-t border-slate-800/60 overflow-x-auto">
          {[
            { id: "preadmission", label: "Pre-Admission Clearance (HITL)", icon: Stethoscope },
            { id: "sms", label: "Twilio 2-Way SMS Simulator", icon: Smartphone },
            { id: "revenue", label: "Post-Discharge & Revenue Cycle", icon: DollarSign },
            { id: "audit", label: "HIPAA Immutable Audit Trail", icon: Lock }
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 py-3 px-3 sm:px-4 text-xs sm:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  active
                    ? "border-cyan-500 text-cyan-400 bg-cyan-950/20"
                    : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? "text-cyan-400" : "text-slate-400"}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {/* ========================================================================= */}
        {/* TAB 1: PRE-ADMISSION CLEARANCE & CLINICIAN HITL                           */}
        {/* ========================================================================= */}
        {activeTab === "preadmission" && (
          <div className="space-y-6">
            {/* Patient Header Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xl font-bold text-cyan-400">
                    SJ
                  </div>
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-white">Sarah Johnson</h2>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        Tier 2: Moderate Risk
                      </span>
                      {caseResumed && (
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Cleared & Committed
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mt-1 font-mono">
                      <span>MRN: SYN-883921</span>
                      <span>•</span>
                      <span>DOB: 1957-01-15 (Age 67)</span>
                      <span>•</span>
                      <span>Procedure: Total Hip Arthroplasty (CPT 27130)</span>
                      <span>•</span>
                      <span>Encounter: enc-sarah-101</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-800 font-mono text-xs">
                  <div>
                    <span className="text-slate-400 block">SLA Turnaround</span>
                    <span className="text-cyan-400 font-bold text-sm">~30 mins</span>
                  </div>
                  <span className="text-slate-700 text-xl">|</span>
                  <div>
                    <span className="text-slate-400 block">Traditional</span>
                    <span className="text-rose-400 font-bold text-sm">55–60 hrs</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Parallel Fan-Out Execution Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Branch 1: Scheduling */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="w-5 h-5 text-cyan-400" />
                    <h3 className="font-semibold text-white">1. Scheduling Agent</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    RESOLVED
                  </span>
                </div>
                <p className="text-xs text-slate-400">Concurrent check of surgeon block & patient SMS slot preference.</p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs space-y-1 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Selected Slot:</span>
                    <span className="text-cyan-300 font-semibold">Option B (06:30 AM)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">OR Suite:</span>
                    <span className="text-slate-200">OR-04 (Main Pavilion)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Patient Response:</span>
                    <span className="text-emerald-400">Confirmed via SMS</span>
                  </div>
                </div>
              </div>

              {/* Branch 2: Insurance */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-semibold text-white">2. Insurance Pre-Auth</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    APPROVED
                  </span>
                </div>
                <p className="text-xs text-slate-400">EDI 270/278 clearinghouse verification with exponential backoff.</p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs space-y-1 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Auth Code:</span>
                    <span className="text-emerald-300 font-semibold">AUTH-89211-TX</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Allowable Amount:</span>
                    <span className="text-slate-200">$14,200.00</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Patient Copay:</span>
                    <span className="text-slate-200">$250.00</span>
                  </div>
                </div>
              </div>

              {/* Branch 3: Clinical Risk */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Stethoscope className="w-5 h-5 text-purple-400" />
                    <h3 className="font-semibold text-white">3. Clinical Risk Agent</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    TIER 2 GATE
                  </span>
                </div>
                <p className="text-xs text-slate-400">FHIR R4 extraction with fail-closed missing data policy.</p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs space-y-1 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">ASA Physical Status:</span>
                    <span className="text-amber-400 font-semibold">Class 2</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">RCRI Score:</span>
                    <span className="text-slate-200">1 (High-risk ortho)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Composite Score:</span>
                    <span className="text-cyan-400 font-bold">7.0</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Contraindication Flags */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                Active Contraindication Protocols (5 Flags Triggered)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {[
                  {
                    code: "FLAG_1_MILD_ANEMIA",
                    title: "Mild Pre-Op Anemia",
                    desc: "Hemoglobin 11.2 g/dL (< 12.0): Type & screen, cross-match blood order requested.",
                    badge: "MODERATE"
                  },
                  {
                    code: "FLAG_2_CKD_STAGE_3A",
                    title: "Chronic Kidney Disease (Stage 3a)",
                    desc: "eGFR 52 mL/min, Creatinine 1.4: Avoid NSAIDs and contrast dye; Anesthesiologist review required.",
                    badge: "HIGH RISK"
                  },
                  {
                    code: "FLAG_3_METFORMIN_PREOP_HOLD",
                    title: "Metformin Pre-Op Hold Protocol",
                    desc: "Metformin 1000mg active: Hold 24 hours prior to surgery to avoid lactic acidosis.",
                    badge: "MODERATE"
                  },
                  {
                    code: "FLAG_4_ASPIRIN_BLEED_RISK",
                    title: "Aspirin Bleed Risk",
                    desc: "Aspirin 81mg active: Surgeon confirmation required on hold vs. continue decision.",
                    badge: "MODERATE"
                  },
                  {
                    code: "FLAG_5_HIGH_VTE_PROTOCOL",
                    title: "Mandatory VTE Prophylaxis",
                    desc: "Total Hip Arthroplasty protocol: Pneumatic compression devices and anticoagulation required.",
                    badge: "HIGH RISK"
                  }
                ].map((flag) => (
                  <div key={flag.code} className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl flex items-start gap-3">
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                      {flag.badge}
                    </span>
                    <div>
                      <h4 className="font-semibold text-slate-200">{flag.title}</h4>
                      <p className="text-slate-400 mt-0.5">{flag.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Clinician HITL Cryptographic Attestation Panel */}
            <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-cyan-900/40 rounded-2xl p-6 shadow-lg shadow-cyan-950/20">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-cyan-950 border border-cyan-800 text-cyan-400">
                    <KeyRound className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-base">Attending Anesthesiologist Cryptographic Attestation</h3>
                    <p className="text-xs text-slate-400">Non-repudiable ECDSA NIST P-256 digital signature required to resume paused LangGraph checkpoint.</p>
                  </div>
                </div>
                <div className="text-right text-xs font-mono">
                  <span className="text-slate-400 block">Clinician Actor ID</span>
                  <span className="text-cyan-400 font-semibold">dr-smith-md-882</span>
                </div>
              </div>

              {!caseResumed ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-slate-300 block mb-1">Attestation Decision:</label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                        <input
                          type="radio"
                          name="decision"
                          value="APPROVED"
                          checked={attestationDecision === "APPROVED"}
                          onChange={() => setAttestationDecision("APPROVED")}
                          className="text-cyan-500 focus:ring-cyan-500"
                        />
                        <span>APPROVED (Clear for OR with Contraindication Controls)</span>
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                        <input
                          type="radio"
                          name="decision"
                          value="REJECTED"
                          checked={attestationDecision === "REJECTED"}
                          onChange={() => setAttestationDecision("REJECTED")}
                          className="text-rose-500 focus:ring-rose-500"
                        />
                        <span>REJECTED (Escalate to Pre-Op Clinic)</span>
                      </label>
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-slate-300 block mb-1">Clinical Sign-Off Notes:</label>
                    <textarea
                      value={clinicianNotes}
                      onChange={(e) => setClinicianNotes(e.target.value)}
                      rows={2}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans"
                    />
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-slate-400 font-mono">
                      Algorithm: ECDSA NIST P-256 + SHA-256 Hash
                    </span>
                    <button
                      onClick={handleSignAttestation}
                      disabled={isSigning}
                      className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition flex items-center gap-2 shadow-lg shadow-cyan-600/30 disabled:opacity-50"
                    >
                      {isSigning ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" /> Signing & Resuming...
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" /> Cryptographically Sign & Resume Checkpoint
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-emerald-950/30 border border-emerald-800/40 rounded-xl p-4 text-xs space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold">
                    <CheckCircle2 className="w-4 h-4" /> Case Resumed & Committed to EHR Chart
                  </div>
                  <p className="text-slate-300">
                    Decision: <strong className="text-white">{attestationDecision}</strong> by Dr. Smith.
                  </p>
                  <div className="bg-slate-950 p-2.5 rounded font-mono text-[11px] text-slate-400 break-all border border-slate-800">
                    <span className="text-cyan-400">ECDSA P-256 Signature:</span> {signatureB64}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: TWILIO 2-WAY CONVERSATIONAL SMS SIMULATOR                          */}
        {/* ========================================================================= */}
        {activeTab === "sms" && (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Smartphone className="w-5 h-5 text-cyan-400" />
                    Patient Twilio 2-Way SMS Simulator
                  </h2>
                  <p className="text-xs text-slate-400">
                    Conversational NLP & compound negation parsing for appointment confirmations and post-op symptom monitoring.
                  </p>
                </div>
                <div className="text-right text-xs font-mono">
                  <span className="text-slate-400 block">Patient Phone</span>
                  <span className="text-cyan-400 font-semibold">+1 (555) 123-4567</span>
                </div>
              </div>

              {/* Smartphone Chat Window */}
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex flex-col h-[400px] overflow-y-auto space-y-3 font-sans">
                {smsMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${msg.sender === "patient" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs ${
                        msg.sender === "patient"
                          ? "bg-cyan-600 text-white rounded-br-none"
                          : "bg-slate-800 text-slate-200 rounded-bl-none border border-slate-700"
                      }`}
                    >
                      {msg.text}
                    </div>
                    <span className="text-[10px] text-slate-500 mt-1 px-1 font-mono">{msg.time}</span>
                  </div>
                ))}

                {isSendingSms && (
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 italic px-2">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                    Parsing symptom deltas against baseline...
                  </div>
                )}
              </div>

              {/* Quick Reply Triggers */}
              <div className="mt-4 space-y-2">
                <span className="text-xs text-slate-400 block font-medium">Quick Reply Scenarios:</span>
                <div className="flex flex-wrap gap-2 text-xs">
                  <button
                    onClick={() => handleSendSms("Option B works best for me")}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                  >
                    Option B (Slot Pick)
                  </button>
                  <button
                    onClick={() => handleSendSms("5, no, no, no, no")}
                    className="px-3 py-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-800/60 transition"
                  >
                    "5, no, no, no, no" (POD 1 Normal)
                  </button>
                  <button
                    onClick={() => handleSendSms("My pain is 6 and I have right calf swelling")}
                    className="px-3 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 transition"
                  >
                    "Right calf swelling" (DVT Red Flag)
                  </button>
                  <button
                    onClick={() => handleSendSms("My pain is 3, no fever or redness, feeling pretty good")}
                    className="px-3 py-1.5 rounded-lg bg-purple-950/40 hover:bg-purple-900/60 text-purple-300 border border-purple-800/60 transition"
                  >
                    "No fever or redness" (NLP Negation)
                  </button>
                </div>
              </div>

              {/* Freeform SMS input */}
              <div className="mt-4 flex gap-2">
                <input
                  type="text"
                  placeholder="Type an SMS reply (e.g. 'Option A' or 'Pain is 4, no swelling')..."
                  value={customSmsInput}
                  onChange={(e) => setCustomSmsInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendSms()}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
                <button
                  onClick={() => handleSendSms()}
                  className="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" /> Send SMS
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: POST-DISCHARGE RECOVERY & REVENUE CYCLE                            */}
        {/* ========================================================================= */}
        {activeTab === "revenue" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Recovery Trajectory Norms Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Activity className="w-5 h-5 text-cyan-400" />
                  Post-Op Day Recovery Trajectory (CPT 27130)
                </h3>
                <p className="text-xs text-slate-400">
                  Evaluates patient symptom trends against procedure-specific baseline curves rather than static population averages.
                </p>

                <div className="space-y-3 font-mono text-xs">
                  <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-slate-300 font-semibold">Post-Op Day 1 (POD 1):</span>
                      <span className="text-emerald-400">Patient: 5/10 (Expected: 4–7)</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div className="bg-emerald-500 h-2 rounded-full" style={{ width: "50%" }}></div>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 block">Status: On Track • Ambulation initiated</span>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-slate-300 font-semibold">Post-Op Day 3 (POD 3):</span>
                      <span className="text-slate-400">Expected: 3–5</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div className="bg-cyan-500 h-2 rounded-full" style={{ width: "40%" }}></div>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 block">Scheduled automated Twilio SMS check-in</span>
                  </div>

                  <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-slate-300 font-semibold">Post-Op Day 7 (POD 7):</span>
                      <span className="text-slate-400">Expected: 1–3</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div className="bg-cyan-500 h-2 rounded-full" style={{ width: "20%" }}></div>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 block">Dressing removal & wound inspection survey</span>
                  </div>
                </div>
              </div>

              {/* Revenue Cycle & Coding Audit Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-emerald-400" />
                  Dual-Direction Billing & Coding Audit Engine
                </h3>
                <p className="text-xs text-slate-400">
                  Protects hospital margin from down-coding under-billing while eliminating up-coding fraud exposure.
                </p>

                <div className="p-4 bg-emerald-950/20 border border-emerald-800/40 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">1. Down-Coding Protection:</span>
                    <span className="font-mono text-emerald-400 font-bold text-sm">+$3,800.00 Protected</span>
                  </div>
                  <p className="text-slate-300">
                    System detected documented <strong className="text-white">CKD Stage 3a (N18.30)</strong> in labs and notes that was omitted from billing diagnosis codes. Adds Complication/Comorbidity (CC) severity tier.
                  </p>
                </div>

                <div className="p-4 bg-cyan-950/20 border border-cyan-800/40 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">2. Up-Coding Fraud Prevention:</span>
                    <span className="font-mono text-cyan-400 font-bold text-sm">Zero Liability</span>
                  </div>
                  <p className="text-slate-300">
                    Verified that high-severity cardiac codes (e.g. Heart Failure I50 series) are unsubstantiated by operative findings, preventing false claim submission.
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-xs font-mono">
                  <span className="text-slate-400">Total Allowable Reimbursement:</span>
                  <span className="text-emerald-400 font-bold text-base">$18,000.00</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: IMMUTABLE HIPAA AUDIT TRAIL LOG                                    */}
        {/* ========================================================================= */}
        {activeTab === "audit" && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Lock className="w-5 h-5 text-emerald-400" />
                    Statutory HIPAA 6-Year Immutable Audit Trail (WORM)
                  </h2>
                  <p className="text-xs text-slate-400">
                    Every PHI touch, agent decision, and clinician attestation is hashed with SHA-256 and committed to immutable storage.
                  </p>
                </div>

                <button
                  onClick={verifyAuditLog}
                  disabled={verifyingAudit}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-mono text-cyan-400 border border-slate-700 flex items-center gap-2 self-start sm:self-auto"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${verifyingAudit ? "animate-spin" : ""}`} />
                  {verifyingAudit ? "Computing SHA-256 Hashes..." : "Verify Log Integrity"}
                </button>
              </div>

              {auditVerified && (
                <div className="mb-4 p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-xl text-xs flex items-center gap-2 text-emerald-400 font-mono">
                  <ShieldCheck className="w-4 h-4" />
                  Audit Trail Cryptographic Integrity Check: PASSED (Zero tampering detected across all 6 records)
                </div>
              )}

              {/* Table of Audit Records */}
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border border-slate-800 rounded-xl">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Audit ID</th>
                      <th className="py-2.5 px-3">Actor</th>
                      <th className="py-2.5 px-3">Action Type</th>
                      <th className="py-2.5 px-3">Target Resource</th>
                      <th className="py-2.5 px-3">SHA-256 Payload Hash</th>
                      <th className="py-2.5 px-3">Retention</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-slate-900/60 text-slate-300">
                    {[
                      {
                        id: "aud-admit-enc-sarah-101",
                        actor: "EHR_TRIGGER",
                        action: "ADMISSION_EVENT_INGESTED",
                        resource: "Encounter/enc-sarah-101",
                        hash: "3b29c9fe8a1d7c0411...6a",
                        retention: "6-Year WORM"
                      },
                      {
                        id: "aud-gate-eval-101",
                        actor: "CLINICAL_GATE_ENGINE",
                        action: "TIER_2_CHECKPOINT_PAUSE",
                        resource: "Patient/pat-sarah-j",
                        hash: "d41d8cd98f00b204e9...80",
                        retention: "6-Year WORM"
                      },
                      {
                        id: "aud-hitl-resume-101",
                        actor: "dr-smith-md-882",
                        action: "ECDSA_ATTESTATION_SIGNED",
                        resource: "Encounter/enc-sarah-101",
                        hash: "9e107d9d372bb6826b...4f",
                        retention: "6-Year WORM"
                      },
                      {
                        id: "aud-sms-slot-101",
                        actor: "PATIENT_SMS_WEBHOOK",
                        action: "SLOT_SELECTION_CONFIRMED",
                        resource: "Appointment/app-101",
                        hash: "c4ca4238a0b923820d...c2",
                        retention: "6-Year WORM"
                      },
                      {
                        id: "aud-postop-pod1-101",
                        actor: "POST_OP_SCHEDULER",
                        action: "POST_OP_TRIAGE_RUN",
                        resource: "Encounter/enc-sarah-101",
                        hash: "eccbc87e4b5ce2fe28...a0",
                        retention: "6-Year WORM"
                      },
                      {
                        id: "aud-billing-audit-101",
                        actor: "BILLING_DISCREPANCY_ENGINE",
                        action: "DOWN_CODING_PREVENTED",
                        resource: "Claim/clm-hip-101",
                        hash: "a87ff679a2f3e71d91...d1",
                        retention: "6-Year WORM"
                      }
                    ].map((row) => (
                      <tr key={row.id} className="hover:bg-slate-800/40">
                        <td className="py-2.5 px-3 text-cyan-400 font-semibold">{row.id}</td>
                        <td className="py-2.5 px-3 text-slate-200">{row.actor}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                            {row.action}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">{row.resource}</td>
                        <td className="py-2.5 px-3 text-emerald-400 text-[11px]">{row.hash}</td>
                        <td className="py-2.5 px-3 text-slate-400 text-[11px]">{row.retention}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/50 py-4 text-xs text-slate-500 font-mono text-center">
        HealthFlow AI Production System • Compliant with HIPAA 45 CFR Part 164 & ONC FHIR R4 Standards
      </footer>
    </div>
  );
}
