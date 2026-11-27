package org.assayflux.rdms.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StudyAccessPolicyTest {
    @Test fun noAssignmentsDenyAccess() {
        assertFalse(StudyAccessPolicy.canRead("u1", "s1", emptyList()))
        assertFalse(StudyAccessPolicy.canWrite("u1", "s1", emptyList()))
    }
    @Test fun viewerCanReadButCannotWrite() {
        val grants = listOf(StudyGrant("u1", "s1", "VIEWER"))
        assertTrue(StudyAccessPolicy.canRead("u1", "s1", grants))
        assertFalse(StudyAccessPolicy.canWrite("u1", "s1", grants))
    }
    @Test fun researcherCanWriteButCannotAdminister() {
        val grants = listOf(StudyGrant("u1", "s1", "RESEARCHER"))
        assertTrue(StudyAccessPolicy.canWrite("u1", "s1", grants))
        assertFalse(StudyAccessPolicy.canAdminister("u1", "s1", grants))
    }
}
