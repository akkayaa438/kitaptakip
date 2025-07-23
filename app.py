import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInAnonymously,
  signInWithCustomToken,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';
import {
  getFirestore,
  doc,
  setDoc,
  updateDoc,
  deleteDoc,
  onSnapshot,
  collection,
  query,
  where,
  addDoc,
  getDocs
} from 'firebase/firestore';

// Firebase yapılandırması ve uygulama kimliği, ortam değişkenlerinden alınır.
// Bu değişkenler Canvas ortamında otomatik olarak sağlanır.
const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;

// Firebase uygulamasını başlat
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// Ana Uygulama Bileşeni
const App = () => {
  const [user, setUser] = useState(null); // Oturum açmış kullanıcı bilgisi
  const [userId, setUserId] = useState(null); // Kullanıcı ID'si
  const [loadingAuth, setLoadingAuth] = useState(true); // Kimlik doğrulama yükleniyor mu?
  const [isAuthReady, setIsAuthReady] = useState(false); // Kimlik doğrulama hazır mı?
  const [currentPage, setCurrentPage] = useState('login'); // Mevcut sayfa (login, register, dashboard)
  const [message, setMessage] = useState(''); // Kullanıcıya gösterilecek mesajlar

  // Firebase kimlik doğrulama durumunu dinle
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        setUserId(currentUser.uid);
        setCurrentPage('dashboard');
      } else {
        setUser(null);
        setUserId(null);
        setCurrentPage('login');
      }
      setLoadingAuth(false);
      setIsAuthReady(true); // Kimlik doğrulama dinleyicisi hazır
    });

    // Başlangıçta özel token ile veya anonim olarak oturum aç
    const signInUser = async () => {
      try {
        if (initialAuthToken) {
          await signInWithCustomToken(auth, initialAuthToken);
        } else {
          await signInAnonymously(auth);
        }
      } catch (error) {
        console.error("Firebase oturum açma hatası:", error);
        setMessage(`Oturum açma hatası: ${error.message}`);
      }
    };

    signInUser();

    return () => unsubscribe(); // Bileşen kaldırıldığında dinleyiciyi temizle
  }, []);

  // Mesajları belirli bir süre sonra temizle
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  // Sayfa değiştirme işlevi
  const navigateTo = (page) => {
    setCurrentPage(page);
    setMessage('');
  };

  // Oturum kapatma işlevi
  const handleSignOut = async () => {
    try {
      await signOut(auth);
      setMessage('Başarıyla çıkış yapıldı.');
      navigateTo('login');
    } catch (error) {
      console.error("Çıkış yapma hatası:", error);
      setMessage(`Çıkış yapma hatası: ${error.message}`);
    }
  };

  if (loadingAuth) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-400 to-indigo-600">
        <div className="text-white text-2xl animate-pulse">Yükleniyor...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-400 to-indigo-600 p-4 font-inter">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-2xl p-6 md:p-8">
        <h1 className="text-4xl font-bold text-center text-gray-800 mb-6">Kitap Takip Uygulaması</h1>
        {message && (
          <div className="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded relative mb-4" role="alert">
            <span className="block sm:inline">{message}</span>
          </div>
        )}

        {currentPage === 'login' && (
          <Auth
            type="login"
            navigateTo={navigateTo}
            setMessage={setMessage}
          />
        )}
        {currentPage === 'register' && (
          <Auth
            type="register"
            navigateTo={navigateTo}
            setMessage={setMessage}
          />
        )}
        {currentPage === 'forgotPassword' && (
          <Auth
            type="forgotPassword"
            navigateTo={navigateTo}
            setMessage={setMessage}
          />
        )}
        {currentPage === 'dashboard' && user && userId && isAuthReady && (
          <Dashboard
            user={user}
            userId={userId}
            handleSignOut={handleSignOut}
            setMessage={setMessage}
            db={db}
            appId={appId}
          />
        )}
      </div>
    </div>
  );
};

// Kimlik Doğrulama Bileşeni (Giriş, Kayıt, Şifre Sıfırlama)
const Auth = ({ type, navigateTo, setMessage }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      if (type === 'login') {
        await signInWithEmailAndPassword(auth, email, password);
        setMessage('Başarıyla giriş yapıldı!');
      } else if (type === 'register') {
        await createUserWithEmailAndPassword(auth, email, password);
        setMessage('Başarıyla kayıt olundu ve giriş yapıldı!');
      } else if (type === 'forgotPassword') {
        await sendPasswordResetEmail(auth, email);
        setMessage('Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.');
        navigateTo('login');
      }
    } catch (error) {
      console.error("Kimlik doğrulama hatası:", error);
      let errorMessage = 'Bir hata oluştu.';
      if (error.code === 'auth/invalid-email') {
        errorMessage = 'Geçersiz e-posta adresi.';
      } else if (error.code === 'auth/user-disabled') {
        errorMessage = 'Bu kullanıcı hesabı devre dışı bırakıldı.';
      } else if (error.code === 'auth/user-not-found') {
        errorMessage = 'Kullanıcı bulunamadı.';
      } else if (error.code === 'auth/wrong-password') {
        errorMessage = 'Yanlış şifre.';
      } else if (error.code === 'auth/email-already-in-use') {
        errorMessage = 'Bu e-posta adresi zaten kullanımda.';
      } else if (error.code === 'auth/weak-password') {
        errorMessage = 'Şifre en az 6 karakter olmalıdır.';
      } else if (error.code === 'auth/missing-email') {
        errorMessage = 'E-posta adresi boş bırakılamaz.';
      }
      setMessage(`Hata: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const title =
    type === 'login'
      ? 'Giriş Yap'
      : type === 'register'
      ? 'Kayıt Ol'
      : 'Şifremi Unuttum';
  const buttonText =
    type === 'login'
      ? 'Giriş Yap'
      : type === 'register'
      ? 'Kayıt Ol'
      : 'Şifre Sıfırlama Bağlantısı Gönder';

  return (
    <div className="p-6 bg-gray-50 rounded-lg shadow-inner">
      <h2 className="text-2xl font-semibold text-center text-gray-700 mb-6">{title}</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">E-posta</label>
          <input
            type="email"
            id="email"
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>
        {type !== 'forgotPassword' && (
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">Şifre</label>
            <input
              type="password"
              id="password"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={type === 'login' ? 'current-password' : 'new-password'}
            />
          </div>
        )}
        <button
          type="submit"
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
          disabled={loading}
        >
          {loading ? 'Yükleniyor...' : buttonText}
        </button>
      </form>
      <div className="mt-6 text-center">
        {type === 'login' && (
          <>
            <button
              onClick={() => navigateTo('register')}
              className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mr-4"
            >
              Hesabın yok mu? Kayıt Ol
            </button>
            <button
              onClick={() => navigateTo('forgotPassword')}
              className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
            >
              Şifremi Unuttum
            </button>
          </>
        )}
        {type === 'register' && (
          <button
            onClick={() => navigateTo('login')}
            className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
          >
            Zaten hesabın var mı? Giriş Yap
          </button>
        )}
        {type === 'forgotPassword' && (
          <button
            onClick={() => navigateTo('login')}
            className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
          >
            Giriş sayfasına geri dön
          </button>
        )}
      </div>
    </div>
  );
};

// Ana Gösterge Paneli Bileşeni
const Dashboard = ({ user, userId, handleSignOut, setMessage, db, appId }) => {
  const [books, setBooks] = useState([]); // Kullanıcının kitapları
  const [newBookTitle, setNewBookTitle] = useState(''); // Yeni kitap başlığı
  const [newBookTotalPages, setNewBookTotalPages] = useState(''); // Yeni kitap toplam sayfa sayısı
  const [showConfirmModal, setShowConfirmModal] = useState(false); // Onay modalını göster
  const [bookToDelete, setBookToDelete] = useState(null); // Silinecek kitap ID'si

  const today = new Date().toLocaleDateString('tr-TR', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  // Firestore'dan kitapları gerçek zamanlı olarak dinle
  useEffect(() => {
    if (!userId) return; // userId yoksa dinlemeyi başlatma

    const booksCollectionRef = collection(db, `artifacts/${appId}/users/${userId}/books`);
    const q = query(booksCollectionRef);

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const booksData = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
      }));
      setBooks(booksData);
    }, (error) => {
      console.error("Kitapları çekerken hata:", error);
      setMessage(`Kitapları çekerken hata: ${error.message}`);
    });

    return () => unsubscribe(); // Bileşen kaldırıldığında dinleyiciyi temizle
  }, [userId, db, appId, setMessage]);

  // Yeni kitap ekleme işlevi
  const handleAddBook = async (e) => {
    e.preventDefault();
    if (!newBookTitle.trim() || !newBookTotalPages.trim()) {
      setMessage('Kitap başlığı ve toplam sayfa sayısı boş bırakılamaz.');
      return;
    }
    if (isNaN(parseInt(newBookTotalPages)) || parseInt(newBookTotalPages) <= 0) {
      setMessage('Toplam sayfa sayısı pozitif bir sayı olmalıdır.');
      return;
    }

    try {
      const booksCollectionRef = collection(db, `artifacts/${appId}/users/${userId}/books`);
      await addDoc(booksCollectionRef, {
        title: newBookTitle,
        totalPages: parseInt(newBookTotalPages),
        pagesRead: 0,
        lastPageRead: 0,
        createdAt: new Date(),
        userId: userId, // Güvenlik kuralı için userId'yi de sakla
      });
      setMessage('Kitap başarıyla eklendi!');
      setNewBookTitle('');
      setNewBookTotalPages('');
    } catch (error) {
      console.error("Kitap ekleme hatası:", error);
      setMessage(`Kitap ekleme hatası: ${error.message}`);
    }
  };

  // Okunan sayfa sayısını güncelleme işlevi
  const handleUpdatePagesRead = async (bookId, currentPagesRead, currentTotalPages, newPagesToday) => {
    const pagesToday = parseInt(newPagesToday);
    if (isNaN(pagesToday) || pagesToday < 0) {
      setMessage('Okunan sayfa sayısı negatif olamaz.');
      return;
    }

    const updatedPagesRead = currentPagesRead + pagesToday;
    const updatedLastPageRead = currentTotalPages >= updatedPagesRead ? updatedPagesRead : currentTotalPages;

    try {
      const bookDocRef = doc(db, `artifacts/${appId}/users/${userId}/books`, bookId);
      await updateDoc(bookDocRef, {
        pagesRead: updatedPagesRead,
        lastPageRead: updatedLastPageRead,
      });
      setMessage('Okunan sayfa sayısı güncellendi!');
    } catch (error) {
      console.error("Sayfa güncelleme hatası:", error);
      setMessage(`Sayfa güncelleme hatası: ${error.message}`);
    }
  };

  // Kitap silme onayını göster
  const confirmDeleteBook = (bookId) => {
    setBookToDelete(bookId);
    setShowConfirmModal(true);
  };

  // Kitap silme işlevi
  const handleDeleteBook = async () => {
    if (!bookToDelete) return;

    try {
      const bookDocRef = doc(db, `artifacts/${appId}/users/${userId}/books`, bookToDelete);
      await deleteDoc(bookDocRef);
      setMessage('Kitap başarıyla silindi!');
    } catch (error) {
      console.error("Kitap silme hatası:", error);
      setMessage(`Kitap silme hatası: ${error.message}`);
    } finally {
      setShowConfirmModal(false);
      setBookToDelete(null);
    }
  };

  return (
    <div className="p-6 bg-gray-50 rounded-lg shadow-inner">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-gray-800">Hoş Geldiniz, {user.email || 'Kullanıcı'}!</h2>
          <p className="text-gray-600 text-sm">Kullanıcı ID'niz: <span className="font-mono text-xs bg-gray-200 px-2 py-1 rounded">{userId}</span></p>
          <p className="text-gray-600 text-sm">Bugün: {today}</p>
        </div>
        <button
          onClick={handleSignOut}
          className="px-4 py-2 bg-red-500 text-white rounded-md shadow-md hover:bg-red-600 transition duration-150 ease-in-out"
        >
          Çıkış Yap
        </button>
      </div>

      {/* Yeni Kitap Ekle Formu */}
      <div className="mb-8 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
        <h3 className="text-xl font-medium text-gray-700 mb-4">Yeni Kitap Ekle</h3>
        <form onSubmit={handleAddBook} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-1">
            <label htmlFor="bookTitle" className="block text-sm font-medium text-gray-700">Kitap Başlığı</label>
            <input
              type="text"
              id="bookTitle"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={newBookTitle}
              onChange={(e) => setNewBookTitle(e.target.value)}
              required
            />
          </div>
          <div className="md:col-span-1">
            <label htmlFor="totalPages" className="block text-sm font-medium text-gray-700">Toplam Sayfa Sayısı</label>
            <input
              type="number"
              id="totalPages"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={newBookTotalPages}
              onChange={(e) => setNewBookTotalPages(e.target.value)}
              required
              min="1"
            />
          </div>
          <div className="md:col-span-1">
            <button
              type="submit"
              className="w-full py-2 px-4 bg-green-600 text-white rounded-md shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-150 ease-in-out"
            >
              Kitap Ekle
            </button>
          </div>
        </form>
      </div>

      {/* Kitap Listesi */}
      <h3 className="text-xl font-medium text-gray-700 mb-4">Kitaplarım</h3>
      {books.length === 0 ? (
        <p className="text-gray-500 text-center">Henüz kaydedilmiş bir kitabınız yok. Yukarıdan yeni bir kitap ekleyin!</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {books.map((book) => (
            <div key={book.id} className="bg-white rounded-lg shadow-md p-5 border border-gray-200">
              <h4 className="text-lg font-semibold text-gray-800 mb-2">{book.title}</h4>
              <p className="text-gray-600 text-sm mb-1">Toplam Sayfa: <span className="font-medium">{book.totalPages}</span></p>
              <p className="text-gray-600 text-sm mb-1">Okunan Sayfa: <span className="font-medium">{book.pagesRead}</span></p>
              <p className="text-gray-600 text-sm mb-3">Son Okunan Sayfa: <span className="font-medium">{book.lastPageRead}</span></p>

              <div className="flex items-center space-x-2 mb-4">
                <input
                  type="number"
                  placeholder="Bugün okunan sayfa"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  min="0"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleUpdatePagesRead(book.id, book.pagesRead, book.totalPages, e.target.value);
                      e.target.value = ''; // Input'u temizle
                    }
                  }}
                />
                <button
                  onClick={(e) => {
                    const input = e.target.previousElementSibling;
                    handleUpdatePagesRead(book.id, book.pagesRead, book.totalPages, input.value);
                    input.value = ''; // Input'u temizle
                  }}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md shadow-md hover:bg-blue-600 transition duration-150 ease-in-out text-sm"
                >
                  Güncelle
                </button>
              </div>

              <button
                onClick={() => confirmDeleteBook(book.id)}
                className="w-full py-2 px-4 bg-red-500 text-white rounded-md shadow-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition duration-150 ease-in-out"
              >
                Sil
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Onay Modalı */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm mx-auto">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Silme Onayı</h3>
            <p className="text-gray-600 mb-6">Bu kitabı silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.</p>
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md shadow-sm hover:bg-gray-400 transition duration-150 ease-in-out"
              >
                İptal
              </button>
              <button
                onClick={handleDeleteBook}
                className="px-4 py-2 bg-red-600 text-white rounded-md shadow-sm hover:bg-red-700 transition duration-150 ease-in-out"
              >
                Evet, Sil
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
