/*
 * Jenkins startup script: create the admin user and mark setup complete.
 *
 * Runs automatically from $JENKINS_HOME/init.groovy.d on every boot. Together
 * with -Djenkins.install.runSetupWizard=false in JAVA_OPTS this removes the
 * interactive setup wizard, so the controller comes up fully configured and
 * reproducible - the same "configuration as code" idea as the rest of this
 * repository.
 *
 * The credentials come from the environment (JENKINS_ADMIN_USER /
 * JENKINS_ADMIN_PASSWORD, supplied by the git-ignored .env file), never from
 * this file, so no password is committed.
 */
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.install.InstallState
import jenkins.model.Jenkins

def instance = Jenkins.get()

def adminUser = System.getenv('JENKINS_ADMIN_USER') ?: 'admin'
def adminPassword = System.getenv('JENKINS_ADMIN_PASSWORD')

if (!adminPassword) {
    throw new IllegalStateException(
            'JENKINS_ADMIN_PASSWORD is not set - see .env.example')
}

// Only create the realm once; re-running must not reset an existing password.
if (!(instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm)) {
    def realm = new HudsonPrivateSecurityRealm(false, false, null)
    realm.createAccount(adminUser, adminPassword)
    instance.setSecurityRealm(realm)

    def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
    strategy.setAllowAnonymousRead(false)
    instance.setAuthorizationStrategy(strategy)

    instance.save()
    println "init.groovy.d: created admin user '${adminUser}'"
} else {
    println 'init.groovy.d: security realm already configured, leaving it alone'
}

// Skip the "new Jenkins" wizard entirely.
if (!instance.installState.isSetupComplete()) {
    InstallState.INITIAL_SETUP_COMPLETED.initializeState()
    println 'init.groovy.d: marked initial setup as complete'
}
