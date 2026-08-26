import { useState } from 'react';

export const useRazorpay = (userId, profile = null) => {
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState(null);

    const processPayment = async (amount) => {
        setIsProcessing(true);
        setError(null);

        return new Promise(async (resolve, reject) => {
            if (!window.Razorpay) {
                const msg = 'Razorpay SDK failed to load';
                setError(msg);
                setIsProcessing(false);
                reject(new Error(msg));
                return;
            }

            try {
                // 1. Create order
                const orderRes = await fetch('http://localhost:9000/api/v1/wallet/create-order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, amount })
                });
                const orderData = await orderRes.json();
                if (!orderRes.ok) throw new Error(orderData.detail || 'Failed to create order');

                // Save the user_id if it was created on the backend
                if (orderData.user_id && !userId) {
                    sessionStorage.setItem('paisaan_user_id', orderData.user_id);
                }

                // 2. Open Razorpay checkout
                const options = {
                    key: orderData.key_id,
                    amount: orderData.amount * 100,
                    currency: orderData.currency,
                    name: "Paisaan Wallet",
                    description: "Add funds to virtual wallet",
                    order_id: orderData.order_id,
                    handler: async function (response) {
                        try {
                            // 3. Verify payment
                            const verifyRes = await fetch('http://localhost:9000/api/v1/wallet/verify-payment', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    razorpay_order_id: response.razorpay_order_id,
                                    razorpay_payment_id: response.razorpay_payment_id,
                                    razorpay_signature: response.razorpay_signature,
                                    user_id: orderData.user_id || userId
                                })
                            });
                            const verifyData = await verifyRes.json();
                            if (!verifyRes.ok) throw new Error(verifyData.detail || 'Payment verification failed');

                            setIsProcessing(false);
                            resolve(response.razorpay_payment_id || 'success');
                        } catch (err) {
                            setIsProcessing(false);
                            setError(err.message);
                            reject(err);
                        }
                    },
                    prefill: {
                        name: profile?.name || "Paisaan User",
                    },
                    theme: { color: "#3399cc" },
                    modal: {
                        ondismiss: function() {
                            setIsProcessing(false);
                            reject(new Error("Payment modal closed by user"));
                        }
                    }
                };
                const rzp = new window.Razorpay(options);
                rzp.on('payment.failed', function (response) {
                    setIsProcessing(false);
                    setError(response.error.description);
                    reject(new Error(response.error.description));
                });
                rzp.open();
            } catch (err) {
                setIsProcessing(false);
                setError(err.message);
                reject(err);
            }
        });
    };

    return { processPayment, isProcessing, error };
};
