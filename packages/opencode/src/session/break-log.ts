export interface BreakLogReport {
  passed: boolean
  exitCode: number
  failedTests: string[]
  stderr: string
  stdout: string
  formattedFeedback: string
  canRetry: boolean
}

export function analyzeTestOutput(
  stdout: string,
  stderr: string,
  exitCode: number,
  attempt: number,
  maxAttempts: number = 5,
): BreakLogReport {
  const passed = exitCode === 0
  const combined = `${stdout}\n${stderr}`
  const failedTests: string[] = []

  if (!passed) {
    const lines = combined.split("\n")
    for (const line of lines) {
      if (line.includes("FAIL") || line.includes("error:") || line.includes("AssertionError") || line.includes("×")) {
        const trimmed = line.trim()
        if (trimmed && !failedTests.includes(trimmed)) {
          failedTests.push(trimmed)
        }
      }
    }
  }

  const isConfigOrEmptyError = combined.includes("do-not-run-tests-from-root") || combined.includes("No tests found")
  const canRetry = !passed && !isConfigOrEmptyError && attempt < maxAttempts

  let formattedFeedback = ""
  if (!passed) {
    formattedFeedback = `### [Break Log - Tentative ${attempt}/${maxAttempts}] Gate 'Test Pass?' Échoué\n\n`
    formattedFeedback += `**Code de sortie** : ${exitCode}\n\n`
    if (failedTests.length > 0) {
      formattedFeedback += `**Tests en échec identifiés** :\n`
      for (const ft of failedTests.slice(0, 10)) {
        formattedFeedback += `- \`${ft}\`\n`
      }
      formattedFeedback += `\n`
    }
    formattedFeedback += `**Extrait de la stack trace / sortie d'erreur** :\n\`\`\`\n`
    const errorSnippet = combined.slice(-2000).trim()
    formattedFeedback += `${errorSnippet || "Aucune sortie capturée"}\n\`\`\`\n\n`
    if (canRetry) {
      formattedFeedback += `> **Instruction d'auto-guérison** : Veuillez analyser l'écart entre le PRD/SRS, l'implémentation (dev_plan) et la suite de tests (test_plan), puis appliquer ou ordonner les corrections nécessaires pour faire passer les tests.`
    } else {
      formattedFeedback += `> **Plafond de tentatives atteint (${maxAttempts}/${maxAttempts})** : Arrêt de la boucle de guérison autonome. Veuillez solliciter l'intervention humaine pour résoudre ce blocage.`
    }
  } else {
    formattedFeedback = `### Gate 'Test Pass?' : SUCCÈS\n\nTous les tests ont été validés avec succès à la tentative ${attempt}/${maxAttempts}. Convergence atteinte.`
  }

  return {
    passed,
    exitCode,
    failedTests,
    stderr,
    stdout,
    formattedFeedback,
    canRetry,
  }
}
