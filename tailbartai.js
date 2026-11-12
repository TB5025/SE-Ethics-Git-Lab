const crypto = require('crypto');

/**
 * Өгөгдлийн сангийн холболт болон аюулгүй query ажиллуулах класс
 * (SQL Injection-ийн эсрэг parameterized query ашиглах)
 */
class DatabaseConnection {
    static async executeQuery(query, params = []) {
        // Энд бодит өгөгдлийн сангийн холболт хийгдэнэ (Жишээ нь: MySQL, PostgreSQL)
        console.log(`[DB Query Executed]: ${query} with params:`, params);
        return [{ id: 1, status: "success" }];
    }
}

/**
 * US-14: Нэвтрэх, эрх удирдах, нууц үгийг hash-лах класс
 */
class AuthenticationManager {
    static hashSalt = "EBS_Schedule_Secure_Salt_2026";

    static hashPassword(password) {
        if (!password || password.length < 6) {
            throw new Error("Нууц үг хамгийн багадаа 6 тэмдэгттэй байх шаардлагатай.");
        }
        return crypto
            .createHash('sha256')
            .update(password + this.hashSalt)
            .digest('hex');
    }

    static async verifyAndGetUser(username, passwordInput) {
        // Input validation (Хэрэглэгчийн оролтыг шалгах)
        const usernameRegex = /^[a-zA-Z0-9_.-]+$/;
        if (!usernameRegex.test(username)) {
            throw new Error("Нэвтрэх нэрийн формат буруу байна.");
        }

        const hashedPassword = this.hashPassword(passwordInput);

        // Аюулгүй Database query (Parameterized)
        const query = "SELECT user_id, username, role, password_hash FROM users WHERE username = ?";
        // const result = await DatabaseConnection.executeQuery(query, [username]);

        // Жишээ зорилгоор олдсон хэрэглэгч
        const mockUser = {
            user_id: 201,
            username: username,
            role: "student", // student, teacher, manager, admin
            password_hash: hashedPassword
        };

        if (mockUser && mockUser.password_hash === hashedPassword) {
            return { 
                success: true, 
                user_id: mockUser.user_id, 
                role: mockUser.role 
            };
        }

        return { success: false, message: "Нэвтрэх нэр эсвэл нууц үг буруу байна." };
    }
}

/**
 * Хичээл сонголт болон давхцал шалгах менежер
 */
class EnrollmentManager {
    constructor() {
        // Санах ойд байгаа хуваарийн болон суудлын жишээ өгөгдөл
        this.enrolledCourses = [];
    }

    async checkScheduleAndSeatAvailability(studentId, courseId) {
        // Цаг давхцсан эсвэл сул суудал дууссан эсэхийг шалгах логик
        console.log(`Checking schedule and seat for Student ID: ${studentId}, Course ID: ${courseId}`);
        // Жишээ болгон үргэлж боломжтой гэж үзвэл:
        return true; 
    }

    async handleSystemError(error) {
        console.error("System Error caught:", error.message);
        return { success: false, message: `Системийн алдаа: ${error.message}` };
    }
}

/**
 * Таны зургаар өгсөн үндсэн логик дараалал:
 * Сурагч нэвтрэх -> Эрх шалгах -> Student ID авах -> Давхцал Сул суудал шалгах -> Enrollment бүртгэх -> Үр дүн буцаах[cite: 7]
 */
async function enrollCourse(username, password, courseId) {
    const enrollmentManager = new EnrollmentManager();
    
    try {
        // 0. Оролтын утга шалгах
        if (!username || !password || !courseId) {
            throw new Error("Мэдээлэл дутуу байна.");
        }

        // 1. Сурагч нэвтрэх & 2. Эрх шалгах
        const authResult = await AuthenticationManager.verifyAndGetUser(username, password);
        if (!authResult.success || authResult.role !== "student") {
            return { success: false, message: "Нэвтрэх эрх хүрэхгүй эсвэл хэрэглэгч олдсонгүй." };
        }

        // 3. Student ID авах
        const studentId = authResult.user_id;

        // 4. Давхцал болон сул суудал шалгах
        const isAvailable = await enrollmentManager.checkScheduleAndSeatAvailability(studentId, courseId);
        if (!isAvailable) {
            return { success: false, message: "Цаг давхцсан эсвэл суудал дүүрэн байна." };
        }

        // 5. Enrollment бүртгэх (Parameterized Database Query)
        const insertQuery = "INSERT INTO Enrollment (student_id, course_id) VALUES (?, ?)";
        const result = await DatabaseConnection.executeQuery(insertQuery, [studentId, courseId]);

        // 6. Үр дүн буцаах
        return { success: true, data: result, message: "Амжилттай бүртгэгдлээ." };

    } catch (error) {
        // Алдааг зохих байдлаар боловсруулах
        return await enrollmentManager.handleSystemError(error);
    }
}

// --- Системийг туршиж үзэх (Execution Example) ---
(async () => {
    console.log("--- Хичээл сонголтын процесс эхэлж байна ---");
    const response = await enrollCourse("student_bold", "SecurePass123", "CS101");
    console.log("Үр дүн:", response);
})();