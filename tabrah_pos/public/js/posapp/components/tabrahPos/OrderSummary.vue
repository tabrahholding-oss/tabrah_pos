<template>
  <v-card elevation="0" class="summary-main-card" style="border: 1px solid #E8E8E8;">
    <v-card class="pa-4 mx-3 mt-3 order-card" style="background: #FAFAFA; border: 1px solid #EEEEEE;" elevation="0">
      <!-- Table Heading -->
      <v-row class="table-header mb-1">
        <v-col cols="5">
          <span class="text-uppercase" style="font-size: 11px; letter-spacing: 0.8px; color: #9E9E9E; font-weight: 600;">Item</span>
        </v-col>
        <v-col cols="2" class="text-center">
          <span class="text-uppercase" style="font-size: 11px; letter-spacing: 0.8px; color: #9E9E9E; font-weight: 600;">Qty</span>
        </v-col>
        <v-col cols="4" class="text-right">
          <span class="text-uppercase" style="font-size: 11px; letter-spacing: 0.8px; color: #9E9E9E; font-weight: 600;">Price</span>
        </v-col>
      </v-row>

      <!-- Image to show when items are empty -->
      <!-- <div v-else class="image-container">
        <img
          src="/assets/tabrah_pos/js/posapp/components/pos"
          alt="No items"
          class="animated-image"
          style=""
        />
      </div> -->

      <!-- Items List -->
      <v-divider style="border-color: #E0E0E0;"></v-divider>
      <v-row v-for="(item, index) in items" :key="item.sku" class="py-1 align-center item-row"
        @click="openDialog(item, true, index)">
        <v-col cols="5" class="pr-0 py-1">
          <div style="font-size: 13px; font-weight: 500; color: #333;">{{ item.item_name }}</div>
          <div style="font-size: 11px; color: #999;">@ {{ item.rate }}</div>
        </v-col>

        <v-col cols="2" class="text-center px-0 py-1">
          <v-chip size="x-small" color="primary" variant="tonal" style="font-weight: 600;">{{ item.qty }}</v-chip>
        </v-col>

        <v-col cols="4" class="text-right py-1">
          <strong style="color: rgb(var(--v-theme-primary)); font-size: 13px;">QAR {{ formatNumber(item.rate * item.qty) }}</strong>
        </v-col>

        <v-col cols="1" class="text-right py-1" v-show="screen == 0">
          <v-icon size="18" @click.stop="requestDeleteItem(index)" color="error" class="delete-icon">mdi-close-circle</v-icon>
        </v-col>

        <v-col cols="12" class="py-0">
          <v-divider style="border-style: dashed; border-color: #E0E0E0;"></v-divider>
        </v-col>
      </v-row>
    </v-card>
    <!-- Persons field above customer select -->
    <v-row class="px-4" v-if="pos_profile.allow_table_no">
      <v-col cols="12" class="mb-0">
        <v-text-field v-model="cover" label="Persons" type="number" min="1" max="99" variant="outlined" class="mr-2 mb-2"></v-text-field>
      </v-col>
    </v-row>
    <!-- Customer select row -->
    <v-row class="px-4">
      <v-col cols="8" class="" style="  height: 64px;">
        <v-autocomplete
          ref="customerSelectRef"
          v-model="selectedCustomer"
          :items="customers"
          :item-title="customerDisplay"
          item-value="name"
          label="Select Customer"
          variant="outlined"
          class="mr-2"
          :custom-filter="customerFilter"
          @update:search-input="onCustomerSearchInput"
        ></v-autocomplete>
      </v-col>
      <v-col cols="4" class="" style="  height: 64px;">
        <v-btn block class="white--text font-weight-bold payment-button" height="52" color="primary"
          @click="addNewCustomer()">
          <v-icon class="mr-2" style="color: white;">mdi-plus</v-icon>
          <p class="mt-2 payment-p">New</p>
        </v-btn>
      </v-col>
    </v-row>

    <v-row justify="center" class="pb-0">
      <v-col cols="12" md="12">
        <v-card class="pa-4 mx-3 payment-card" elevation="0" style="background: #FAFAFA; border: 1px solid #EEEEEE;">
          <!-- Order Summary Header -->
          <v-row justify="space-between" align="center" class="px-3 py-1">
            <v-col cols="6">
              <span style="font-size: 14px; font-weight: 700; color: #333; letter-spacing: 0.3px;">Order Summary</span>
            </v-col>
          </v-row>

          <v-divider class="mb-2" style="border-color: #E0E0E0;"></v-divider>

          <!-- Order Details -->
          <!-- 
          <v-row justify="space-between" class="px-6 py-0">
            <v-col cols="4" class="py-0 payment-text-color">Total items:</v-col>
            <v-col cols="4">
              <v-divider class="dotted-divider"></v-divider>
            </v-col>
            <v-col cols="4" class="text-right py-0 payment-text-color">
              {{ totalItems }}
            </v-col>
          </v-row> -->
          <v-row justify="space-between" class="px-6 pb-0">
            <v-col cols="4" class="py-0 payment-text-color">Total Quantity:</v-col>
            <v-col cols="4">
              <v-divider class="dotted-divider" :thickness="3"></v-divider>
            </v-col>
            <v-col cols="4" class="text-right py-0 payment-text-color">
              {{ totalQuantity }}
            </v-col>
          </v-row>
          <v-row justify="space-between" class="px-6 py-0">
            <v-col cols="4" class="pb-0 payment-text-color">Net Total:</v-col>
            <v-col cols="4">
              <v-divider class="mt-3 dotted-divider" :thickness="3"></v-divider>
            </v-col>
            <v-col cols="4" class="text-right pb-0 payment-text-color">
              QAR. {{ formatNumber(netTotal) }}
            </v-col>
          </v-row>

          <v-row justify="space-between" class="px-6 py-0">
            <v-col cols="4" class="py-0 payment-text-color">GST {{ selectedPaymentMode.tax_rate }}%:</v-col>
            <v-col cols="4">
              <v-divider class="dotted-divider" :thickness="3"></v-divider>
            </v-col>
            <v-col cols="4" class="text-right py-0 payment-text-color">
              QAR. {{ formatNumber(gstAmount) }}
            </v-col>
          </v-row>
          <v-row justify="space-between" class="px-6 py-0" v-if="returnType">
            <v-col cols="4" class="py-0 payment-text-color">Advance Paid:</v-col>
            <v-col cols="4">
              <v-divider class="dotted-divider" :thickness="3"></v-divider>
            </v-col>
            <v-col cols="4" class="text-right py-0 payment-text-color">
              QAR. {{ advanceAmount }}
            </v-col>
          </v-row>
          <v-row justify="space-between" class="px-6 py-0" v-else>
            <v-col cols="4" class="py-0 payment-text-color">Discounts:</v-col>
            <v-col cols="4">
              <v-divider class="dotted-divider" :thickness="3"></v-divider>
            </v-col>
            <v-col cols="4" class="text-right py-0 payment-text-color">
              QAR.0.00
            </v-col>
          </v-row>


          <!-- Grand Total -->
          <div class="grand-total-bar mt-3 mx-3">
            <span style="font-size: 15px; font-weight: 700; color: #333;">Grand Total</span>
            <span class="total-p">QAR {{ formatNumber(grandTotal) }}</span>
          </div>

          <!-- Action Buttons -->
          <div class="px-3 pt-3 pb-1">
            <v-btn
              block
              class="action-btn action-btn-primary mb-2"
              height="44"
              color="primary"
              @click="goForPayment"
              :loading="loadingBtn"
            >
              <v-icon size="18" class="mr-2">mdi-credit-card-outline</v-icon>
              Payment
            </v-btn>

            <v-row dense class="mt-1">
              <v-col :cols="
                (!pos_profile.custom_allow_pre_invoice_print && !pos_profile.custom_allow_kot_print) ? 12 :
                (pos_profile.custom_allow_pre_invoice_print !== pos_profile.custom_allow_kot_print) ? 6 : 4
              ">
                <v-btn
                  block
                  class="action-btn"
                  height="40"
                  color="primary"
                  variant="outlined"
                  @click="holdOrder()"
                  :loading="loadingBtn"
                >
                  <v-icon size="16" class="mr-1">mdi-pause-circle-outline</v-icon>
                  Hold
                </v-btn>
              </v-col>
              <v-col v-if="pos_profile.custom_allow_pre_invoice_print" :cols="(pos_profile.custom_allow_kot_print) ? 4 : 6">
                <v-btn
                  block
                  class="action-btn"
                  height="40"
                  color="secondary"
                  variant="tonal"
                  @click="createPreInvoice()"
                  :disabled="screen != 0"
                >
                  <v-icon size="16" class="mr-1">mdi-receipt-text-outline</v-icon>
                  Pre Invoice
                </v-btn>
              </v-col>
              <v-col v-if="pos_profile.custom_allow_kot_print" :cols="(pos_profile.custom_allow_pre_invoice_print) ? 4 : 6">
                <v-btn
                  block
                  class="action-btn"
                  :class="{ 'printer-btn-disabled': printerDisabled[printer] }"
                  height="40"
                  color="secondary"
                  variant="tonal"
                  @click="pos_profile.custom_allow_kot_multiple_prints == 1 ? openPrinterDialog() : generateKotPrint()"
                  :disabled="screen != 0"
                >
                  <v-icon size="16" class="mr-1">mdi-printer-outline</v-icon>
                  KOT
                </v-btn>
              </v-col>
            </v-row>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Return dialog -->
    <v-dialog v-model="dialog" max-width="800px" persistent>
      <v-card>
        <!-- Dialog Title -->
        <v-card-title class="d-flex justify-space-between pt-5">
          <span class="text-h6">Select Return Invoice</span>
          <v-icon @click="closeReturnDialog()">mdi-close</v-icon>
        </v-card-title>
        <!-- Search Field -->
        <v-card-title class="d-flex justify-space-between pt-1">
          <v-text-field v-model="search" label="Search" variant="outlined" clearable class="mx-4 my-2"
            append-inner-icon="mdi-magnify"></v-text-field>
          <v-btn class="white--text font-weight-bold payment-button mt-3" height="48" color="secondary"
            @click="searchReturnInvoice()" :loading="loadingBtn">
            <p class="mt-2 ">Search</p>
          </v-btn>
        </v-card-title>

        <!-- Table -->
        <v-data-table :headers="headers" :items="returnItems" class="elevation-0 mx-4" hide-default-footer>
          <template #item.customer="{ item }">
            <span>{{ item.customer }}</span>
          </template>
        </v-data-table>

        <!-- Actions -->
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" @click="dialog = false">Close</v-btn>
          <v-btn v-if="returnItems.length > 0" color="primary" @click="loadReturn()"
            :loading="submitLoading">Submit</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>


    <!-- return Dialog -->

    <v-dialog v-model="returnDialog" max-width="741px" height="820" persistent>
      <v-card style="height: 790px; overflow-y: hidden; border-radius: 16px">
        <v-card-title>
          <v-row align="center" justify="space-between" class="py-2">
            <v-col cols="auto" class="d-flex align-center" style="    padding-left: 260px;
">
              <img src="/assets/tabrah_pos/js/posapp/components/pos/returnType.png" alt="" class="" />
              <span class="ml-3" style="font-size: 15px;font-weight: 500;">Choose Return Type</span>
            </v-col>
            <v-col cols="auto">
              <v-card-title class="d-flex justify-end">
                <v-btn variant="text" size="x-small" density="default" color="white" style="background: rgb(var(--v-theme-secondary))"
                  @click="closeReturnDialog()">
                  <v-icon>mdi-close</v-icon>
                </v-btn>
              </v-card-title>
            </v-col>
          </v-row>
        </v-card-title>
        <v-card-text>
          <v-row justify="center" class="" style="    padding-left: 100px;">
            <v-radio-group v-model="returnType" color="primary" inline>
              <v-radio label="Exchange" value="exchange" @click.stop="returnType = 'exchange'"></v-radio>
              <v-radio label="Return" value="return" @click.stop="returnType = 'replace'"
                style="    margin-left: 153px;"></v-radio>
            </v-radio-group>
            <!-- <v-radio label="Refund" value="refund"></v-radio>
            <v-radio label="Points" value="points"></v-radio> -->
          </v-row>

          <v-row>
            <v-col cols="12" class="px-10 pt-15">
              <div style="background: #F3F3F3; border-radius: 12px;" class="px-15 py-5">
                <v-card style="    width: 400px;margin-left: 54px;border-radius: 8px;" class="d-flex justify-center">
                  <v-card-text class="pb-0">

                    <div class="dis-grid">
                      <div class="d-flex justify-space-between px-2">
                        <div class="" style="color: #666666;">{{ returnDoc.name }}</div>
                        <v-chip color="primary" size="small">
                          Completed
                        </v-chip>

                      </div>
                      <p class="mt-1 px-2" style="font-size: 18px;font-weight: 700; color: #666666;">
                        QAR. {{ formatNumber(grandTotal) }}
                      </p>
                    </div>

                    <div class="d-flex py-4 mb-2"
                      style="border-top: 1px solid #D5D5D5;border-bottom: 1px solid #D5D5D5;">
                      <img src="/assets/tabrah_pos/js/posapp/components/pos/account.png" alt="" class=""
                        style="width: 35px;" />
                      <p class="mt-2 ml-2"></p>
                      <span style="border: 1px solid #D5D5D5;margin-left: 70px;"></span>
                      <img src="/assets/tabrah_pos/js/posapp/components/pos/posImg.png" alt="" class="ml-2"
                        style="width: 35px;" />
                      <p class="mt-2 ml-2">{{ returnDoc.pos_profile }}</p>
                    </div>

                    <div class="d-flex  my-3" style="">
                      <img src="/assets/tabrah_pos/js/posapp/components/pos/receipt_long.png" alt="" class=""
                        style="width: 35px;" />
                      <p class="ml-2 mt-2 text-grey">
                        <!-- Display items with "+x more" if more than 6 items -->
                        {{
                          items
                            .slice(0, 6)
                            .map((item) => item.item_name)
                            .join(", ")
                        }}<span v-if="items.length > 6">, +{{ items.length - 6 }} more</span>
                      </p>
                    </div>





                  </v-card-text>
                </v-card>

              </div>
              <div class="px-0 pt-7" style="max-height: 350px; overflow-y: auto;">
                <v-row v-for="(item, index) in returnDoc.items" :key="item.sku" class="py-0 align-center mr-0 "
                  @click="openDialog(item, true, index)">
                  <div style="background: #F3F3F3; width: 100%;" class="d-flex py-3">
                    <v-col cols="5" class="pr-2 pb-0 ml-4 pt-1">
                      <div>{{ item.item_name }}</div>
                      <!-- <div class="text-caption grey--text">{{ item.sku }}</div> -->
                      <div class="text-caption grey--text">{{ item.rate }}</div>
                    </v-col>

                    <v-col cols="2" class="text-center px-0 pb-0">
                      {{ item.qty }}
                    </v-col>

                    <v-col cols="4" class="text-right teal--text text--accent-4 pb-0">
                      <strong>QAR.{{ item.rate * item.qty }}</strong>
                    </v-col>
                    <v-col cols="1" class="text-right pb-0" v-show="returnDoc.items.length > 1">
                      <!-- Delete icon -->
                      <v-icon @click.stop="requestDeleteItem(index)" color="red">mdi-delete</v-icon>
                    </v-col>
                  </div>
                  <v-col cols="12" class="py-0 my-0 px-0">
                    <v-divider class="dotted-divider" :thickness="2"></v-divider>
                  </v-col>
                </v-row>

              </div>

              <div class="pt-5 d-flex justify-center">
                <v-btn class="white--text font-weight-bold payment-button" height="52" color="primary"
                  @click="goForReturnProceed" :loading="submitLoading" style="width: 321px;">
                  <p class="mt-2 payment-p">Proceed</p>
                </v-btn>
              </div>

              <div class="pt-5 d-flex justify-center">
                <v-btn class="white--text font-weight-bold " height="52" variant="text" @click="closeReturnDialog"
                  :loading="loadingBtn" :disabled="loadingBtn" style="width: 321px;">
                  <p class="mt-2 payment-p">Cancel</p>
                </v-btn>
              </div>


            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Add Customer -->
    <v-dialog v-model="showDialog" max-width="500px">
      <v-card style="border-radius: 24px;">
        <!-- Dialog Header -->
        <v-card-title class="d-flex justify-center align-center mt-2">
          <div class="d-flex align-center gap-2">
          </div>
          <div class="d-flex align-center gap-2">
            <v-icon color="#3D464D">mdi-account-plus</v-icon>
            <span style="color: #3D464D; font-size: 15px;font-weight: 500;" class="ml-2">Add Customer</span>
          </div>
          <div style="background: rgb(var(--v-theme-secondary));
              height: 21px;
              border-radius: 15px;
              position: relative;
              left: 139px;">
            <v-icon color="white" size="20px" @click="closeCustomerDialog" style="position: relative;
              bottom: 7px;">mdi-close</v-icon>

          </div>
        </v-card-title>

        <!-- Dialog Content -->
        <v-card-text class="px-15">
          <v-form ref="form" v-model="isFormValid">
            <v-text-field v-model="formData.name" label="Name" outlined required
              :rules="[rules.required]"></v-text-field>

            <v-text-field v-model="formData.phone" label="Phone Number" outlined required
              :rules="[rules.required]"></v-text-field>

            <v-text-field v-model="formData.email" label="Email Address" outlined></v-text-field>

            <v-text-field v-model="formData.address" label="Postal Address" outlined></v-text-field>

            <!-- Submit Button -->
            <v-btn block class="white--text font-weight-bold payment-button" height="45" color="primary"
              @click="submitCustomerDialog" :disabled="!isFormValid" :loading="customerLoading">
              Add Customer
            </v-btn>
          </v-form>

          <!-- Note Section -->
          <!-- <div class="mt-4 text-center">
            <span class="caption">
              NOTE: Looking for an existing customer?
              <a href="#" class="text-decoration-underline">Re-Call Customer</a>
            </span>
          </div> -->
        </v-card-text>
      </v-card>
    </v-dialog>
    <v-dialog v-model="pindialog" max-width="400" persistent>
      <v-card>
        <v-card-title class="d-flex justify-space-between align-center">
          <span class="text-h6">Enter Pin</span>
          <v-icon @click="pindialog = false" class="cursor-pointer">mdi-close</v-icon>
        </v-card-title> <v-card-text>
          <div class="text-center">
            <v-otp-input v-model="otp" type="password" :loading="pinloading" length="5"></v-otp-input>
          </div>
        </v-card-text>

        <v-card-actions class="justify-end">
          <v-btn text="Cancel" @click="pindialog = false"></v-btn>
          <v-btn :disabled="otp.length < 5 || pinloading" color="primary" text="Submit"
            @click="checkAuthAccess"></v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showPrinterDialog" max-width="400px">
      <v-card>
        <v-card-title class="text-h6">Select Printer</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6" v-for="printer in availablePrinters" :key="printer">
              <v-btn
                block
                :class="{ 'printer-btn-disabled': printerDisabled[printer] }"
                color="primary"
                @click="printerDisabled[printer] ? showAlreadyPrintedMessage() : handlePrinterSelect(printer)"
              >
                {{ printerLabels[printer] }}
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showPrinterDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import {
  ref,
  onMounted,
  computed,
  watch,
  onUnmounted,
  onBeforeUnmount,
} from "vue";
import eventBus from "../../bus.js";
import storageService from "../../storageService";
import { printPreInvoice } from "../../preinvoice";
import { printKot } from "../../kotPrint.js";

const items = ref([
  // {
  //   name: "Gul Bahaar",
  //   sku: "SKU:10145687-c12",
  //   qty: 1,
  //   rate: "Rs. 270,000/-",
  //   netTotal: "Rs. 270,000/-",
  // },
]);

const paymentModes = ref([
  // {
  //   type: "Card",
  //   icon: "mdi-credit-card",
  //   selected:false
  // },
  // {
  //   type: "Cash",
  //   icon: "mdi-cash",
  //   selected:true
  // },
  // {
  //   type: "Transfer",
  //   icon: "mdi-swap-horizontal",
  //   selected:false
  // },
]);
const selectedCustomer = ref('');
const customers = ref([
  // Example customer list
  // { text: "John Doe", value: 1 },
  // { text: "Jane Smith", value: 2 },
  // { text: "Alice Johnson", value: 3 },
]);
const showDialog = ref(false); // Control the dialog visibility
const isFormValid = ref(false); // Form validation state
const customerLoading = ref(false); // Form validation state


// Form data
const formData = ref({
  name: "",
  phone: "",
  email: "",
  address: "",
});

// Validation rules
const rules = {
  required: (value) => !!value || "This field is required",
  email: (value) => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return !value || pattern.test(value) || "Invalid email address";
  },
  phone: (value) => {
    const pattern = /^[0-9]{10}$/;
    return pattern.test(value) || "Invalid phone number";
  },
};
const pos_profile = ref("");
const pos_opening_shift = ref("");
const invoice_doc = ref({});
const invoiceItems = ref([]);
const selectedPaymentMode = ref("");
const loadingBtn = ref(false);
const saleOrder = ref(false);
const loadingHold = ref(false);
const saleOrderDetail = ref("");
const selectedOrderType = ref("");
const offlineMode = ref(false);
const punching = ref("completed");
const screen = ref(0);
const speedMbps = ref(null); // Measured internet speed in Mbps
const getSpeedRes = ref(false);
const holdOrderId = ref(null);
const dialog = ref(false);
const exchangeItem = ref(false);
const submitLoading = ref(false);
const search = ref("");
const returnDoc = ref("");
const returnType = ref("");
const selectedTable = ref("");
const advanceAmount = ref(0)
const orderBy = ref("");
const allowedDelete = ref(true);
const pindialog = ref(false);
const otp = ref("");
const pinloading = ref(false);
const cover = ref(1); // Default to 1 person
const pendingDeleteIndex = ref(null);
const showPrinterDialog = ref(false);
const selectedPrinter = ref('');
const availablePrinters = ['grill', 'bar'];
const printerLabels = { grill: 'Grill', bar: 'Bar' };
const printerDisabled = ref({ grill: false, bar: false });

const grandTotalCard = computed(() => {
  return grandTotal.value; // Default to grand total, can be customized based on card payment logic
});
const orderType = ref([]);

const selected = ref([]);
const headers = [
  { title: "Customer", value: "customer" },
  { title: "Date", value: "due_date" },
  { title: "Invoice", value: "name" },
  { title: "Amount", value: "total" },
];
const returnItems = ref([]);
const returnDialog = ref(false);
const returnitems = ref([
  {
    item_name: "Three Milk Cake",
    rate: 120000,
    qty: 2
  },
  {
    item_name: "Three Milk Cake",
    rate: 120000,
    qty: 2
  },

])



const totalQuantity = computed(() => {
  return items.value.reduce((acc, item) => acc + item.qty, 0);
});
const totalItems = computed(() => items.value.length);

// const netTotal = ref(0);
// const gstAmount = ref(0);
// const grandTotal = ref(0);

const netTotal = computed(() => {
  const total = items.value.reduce((acc, item) => acc + item.netTotal, 0);
  let taxrate = selectedPaymentMode.value?.tax_rate / 100 || 0;

  // Calculate GST amount with the correct tax rate
  const gstAmount = parseFloat((total * taxrate).toFixed(2));
  let taxIncludeNetamount = 0;
  if (pos_profile.value.posa_tax_inclusive) {
    taxrate = 1 + selectedPaymentMode.value?.tax_rate / 100 || 0;
    taxIncludeNetamount = total / taxrate;
  }

  // If posa_tax_inclusive is true, subtract GST amount from total
  const finalAmount = pos_profile.value.posa_tax_inclusive
    ? taxIncludeNetamount
    : total;
  return finalAmount;
});

const gstAmount = computed(() => {
  const total = items.value.reduce((acc, item) => acc + item.netTotal, 0);
  let taxrate = selectedPaymentMode.value?.tax_rate / 100 || 0;

  // Calculate GST amount with the correct tax rate
  let gstAmount = parseFloat((total * taxrate).toFixed(2));
  if (pos_profile.value.posa_tax_inclusive) {
    taxrate = 1 + selectedPaymentMode.value?.tax_rate / 100 || 0;
    taxIncludeNetamount = total / taxrate;
    gstAmount = total - taxIncludeNetamount;
  }

  return gstAmount; // 16% GST
});
const grandTotal = computed(() => {
  return netTotal.value + gstAmount.value;
});
// watch(
//   items,
//   (newVal) => {
//     if (newVal) {
//       const total = items.value.reduce(
//         (acc, item) => acc + item.netTotal,
//         0
//       );
//       const taxRate = (selectedPaymentMode.value?.tax_rate || 0) / 100;

//       if (pos_profile.value.posa_tax_inclusive) {
//         // Tax-Inclusive Calculations
//         const taxDivisor = 1 + taxRate;
//         netTotal.value = parseFloat((total / taxDivisor).toFixed(2)); // Net total excluding tax
//         gstAmount.value = parseFloat((total - netTotal.value).toFixed(2)); // GST amount
//         grandTotal.value = total; // Grand total remains the original total
//       } else {
//         // Tax-Exclusive Calculations
//         netTotal.value = parseFloat(total.toFixed(2)); // Net total is the sum of all items
//         gstAmount.value = parseFloat((total * taxRate).toFixed(2)); // GST amount
//         grandTotal.value = parseFloat(
//           (netTotal.value + gstAmount.value).toFixed(2)
//         ); // Grand total
//       }
//     }
//   },
//   { deep: true } // Ensures nested changes in objects are tracked
// );
const formatNumber = (num) => {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
};
const addNewCustomer = () => {
  showDialog.value = true;
}
const checkAuthAccess = () => {
  const isMatch = pos_profile.value.employee_list.some((emp) => emp.pin_for_pos === parseInt(otp.value));
  if (isMatch) {
    allowedDelete.value = true;
    pindialog.value = false;
    otp.value = ''
    // If there is a pending delete, perform it now
    if (pendingDeleteIndex.value !== null) {
      deleteItem(pendingDeleteIndex.value);
      pendingDeleteIndex.value = null;
    }
  }
  else {
    eventBus.emit("show_mesage", {
      text: "Invalid Pin. Please try again!",
      color: "error",
    });
  }

  pinloading.value = false;
};

const submitCustomerDialog = async () => {
  try {
    const args = {
      customer_id: '',
      customer_name: formData.value.name,
      company: pos_profile.value.company,
      mobile_no: formData.value.phone,
      email_id: formData.value.email,
      customer_group: pos_profile.value.customer_groups[0].customer_group,
      method: 'create',
      pos_profile_doc: pos_profile.value,
    };
    customerLoading.value = true
    const response = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.create_customer",
      args: args,
    });
    console.log("res", response)
    if (response.message) {
      eventBus.emit("show_mesage", {
        text: `Customer created successfully...`,
        color: "success",
      });
      frappe.utils.play_sound('submit');
      closeCustomerDialog();
      // Refresh customer list and auto-select new customer
      getCustomerNames(pos_profile.value);
      // Wait a moment for the list to refresh, then select
      setTimeout(() => {
        selectedCustomer.value = response.message.name;
      }, 500);
    } else {
      frappe.utils.play_sound('error');
      eventBus.emit("show_mesage", {
        text: `Customer creation failed.`,
        color: "success",
      });
    }
    customerLoading.value = false
  } catch (error) {
    customerLoading.value = false
    console.error("Error fetching invoice document:", error);
  }
};
const closeCustomerDialog = () => {
  showDialog.value = false;
  formData.value = {
    name: '',
    phone: '',
    email: '',
    address: ''
  };
}
const getCustomerNames = (profile) => {
  frappe.call({
    method: 'tabrah_pos.tabrah_pos.api.posapp.get_customer_names',
    args: {
      pos_profile: profile,
    },
    callback: (response) => {
      if (response.message) {
        const customerData = response.message;
        customers.value = customerData;
        // customers.value = customerData;
        // if (pos_profile.value.posa_local_storage) {
        //   localStorage.setItem('customer_storage', '');
        //   localStorage.setItem('customer_storage', JSON.stringify(customerData));
        // }
      }
    },
  });
};
const changePaymentMode = (mode) => {
  selectedPaymentMode.value = mode;
  paymentModes.value.forEach((item) => {
    if (item == mode) {
      item.selected = true;
    } else {
      item.selected = false;
    }
  });
};
const openDialog = (item, flag, index) => {
  eventBus.emit("open-product-dialog", { product: item, flag, index });
};
const openPrinterDialog = () => {
  // Don't show dialog if network printing is enabled
  if (pos_profile.value.custom_enable_kot_network_printing) {
    generateKotPrint('network');
    return;
  }

  // Check which printers are available (not all items printed)
  const heldOrders = JSON.parse(localStorage.getItem('heldOrders')) || [];
  const currentOrder = heldOrders.find(order => order.id === holdOrderId.value);
  let printedItems = {};
  if (currentOrder) printedItems = { ...(currentOrder.printed_items || {}) };
  // Check for each printer if all items are printed
  availablePrinters.forEach(printer => {
    let allPrinted = items.value.every(item => {
      const p = printedItems[item.item_code]?.[printer];
      return p && p.qty >= item.qty;
    });
    printerDisabled.value[printer] = allPrinted;
  });
  showPrinterDialog.value = true;
}

function handlePrinterSelect(printer) {
  selectedPrinter.value = printer;
  showPrinterDialog.value = false;
  generateKotPrint(printer);
}

function filterNonJuiceBeverageBundleItems(bundle) {
  if (!bundle || !Array.isArray(bundle.items)) return [];
  // define your desired order of item groups
  const groupOrder = ["starter", "main course", "desert"];
  
  //////////////Filter out unwanted item groups
  // let filterItems = bundle.items.filter(sub => {
  //   const subGroup = (sub.custom_item_group || '').toLowerCase();
  //   return subGroup !== 'juice' && subGroup !== 'beverage';
  // });

  ///////////// Sort by custom group order
  filterItems.sort((a, b) => {
    const groupA = (a.custom_item_group || '').toLowerCase();
    const groupB = (b.custom_item_group || '').toLowerCase();

    const indexA = groupOrder.indexOf(groupA);
    const indexB = groupOrder.indexOf(groupB);

    // items in defined groups come first, ordered by groupOrder
    if (indexA !== -1 && indexB !== -1) return indexA - indexB;

    // if one of them is not in groupOrder, it goes after the defined groups
    if (indexA === -1 && indexB !== -1) return 1;
    if (indexA !== -1 && indexB === -1) return -1;

    // if both are outside groupOrder, keep alphabetical
    return groupA.localeCompare(groupB);
  });

return filterItems;
}

const generateKotPrint = async (printerArg = null) => {
  if (items.value.length === 0) return;

  // Load held orders context and previously printed items
  const heldOrders = JSON.parse(localStorage.getItem('heldOrders')) || [];
  const currentOrder = heldOrders.find(order => order.id === holdOrderId.value);
  let printedItems = {};
  if (currentOrder) printedItems = { ...(currentOrder.printed_items || {}) };

  // Prefer an existing token
  let tokenNumber = invoice_doc.value?.custom_token_number || (currentOrder?.custom_token_number || null);

  // Network printing path first
  if (pos_profile.value.custom_enable_kot_network_printing) {
    // Determine items that still need to be printed for network (consolidated key)
    let itemsToPrint = items.value.filter(item => {
      const p = printedItems[item.item_code]?.network;
      const printedQty = p ? p.qty : 0;
      return item.qty > printedQty;
    });

    if (itemsToPrint.length === 0) {
      eventBus.emit('show_mesage', { text: 'Already printed items', color: 'error' });
      return;
    }

    // Generate token only if missing and company matches
    if (!tokenNumber && pos_profile.value.company === "Run of the Mill") {
      try {
        const response = await frappe.call({
          method: "tabrah_pos.tabrah_pos.api.posapp.get_next_token_number",
          args: {
            company: pos_profile.value.company,
            pos_profile: pos_profile.value.name,
            pos_opening_shift: pos_opening_shift.value.name
          }
        });
        if (response.message) {
          tokenNumber = response.message;
          if (!invoice_doc.value) invoice_doc.value = {};
          invoice_doc.value.custom_token_number = tokenNumber;
          // Persist to held order
          if (currentOrder) {
            currentOrder.custom_token_number = tokenNumber;
            const idx = heldOrders.findIndex(o => o.id === currentOrder.id);
            if (idx !== -1) {
              heldOrders[idx] = { ...currentOrder };
              localStorage.setItem('heldOrders', JSON.stringify(heldOrders));
            }
          }
        }
      } catch (error) {
        console.error("Error generating token number:", error);
      }
    }

    const doc = await get_invoice_doc();
    doc.grand_total = grandTotal.value;
    doc.gstAmountCash = gstAmount.value;
    doc.cover = cover.value;
    const now = new Date();
    doc.date = now.toISOString().split('T')[0];
    doc.time = now.toLocaleTimeString('en-US', { hour12: false });
    doc.items = itemsToPrint;
    doc.pos_profile = pos_profile.value;
    if (tokenNumber) {
      doc.custom_token_number = tokenNumber;
    }


    doc.kot_items = itemsToPrint.map(item => {
    let finalQty;
    const p = printedItems[item.item_code]?.network;
    const hasBeenPrinted = !!p;
    if (!hasBeenPrinted) {
      finalQty = item.qty;
    } else {
      const printedQty = p.qty;
      finalQty = item.qty - printedQty;
    }

let filteredBundle = item.product_bundle
      ? {
          ...item.product_bundle,
          items: filterNonJuiceBeverageBundleItems(item.product_bundle)
        }
      : undefined;
    return {
      ...item,
      qty: finalQty,
      product_bundle: filteredBundle,
    };
  });

  const groupOrder = ["hot starters", "cold starters", "sides", "breakfast", "main dishes", "deserts"];



    const groupedItems = [...doc.kot_items].sort((a, b) => {
    const groupA = (a.item_group || "").trim().toLowerCase();
    const groupB = (b.item_group || "").trim().toLowerCase();

    const indexA = groupOrder.indexOf(groupA);
    const indexB = groupOrder.indexOf(groupB);

    // DEBUG: print comparison values

    if (indexA !== -1 && indexB !== -1) return indexA - indexB;
    if (indexA === -1 && indexB !== -1) return 1;
    if (indexA !== -1 && indexB === -1) return -1;
    return groupA.localeCompare(groupB);
  });


  const printDoc = {
    ...doc,
    items: groupedItems,
    pos_profile: pos_profile.value,
  };

    // Update printed map for network
    itemsToPrint.forEach(item => {
      if (!printedItems[item.item_code]) printedItems[item.item_code] = {};
      printedItems[item.item_code].network = {
        qty: item.qty,
        timestamp: new Date().toISOString(),
      };
    });

    holdOrder(printedItems);
    printKot(printDoc);
    return;
  }

  // Local (non-network) printing
  let printer = printerArg;
  if (!printer && pos_profile.value.allow_kot_mulitple_print == 1) {
    openPrinterDialog();
    return;
  }
  if (!printer) printer = 'grill'; // fallback for single printer

  // Determine items that still need to be printed for this specific printer
  let itemsToPrint = items.value.filter(item => {
    const p = printedItems[item.item_code]?.[printer];
    const printedQty = p ? p.qty : 0;
    let group = (item.item_group || '').toLowerCase();
    if (group === 'juice' || group === 'beverage') return false;
    return item.qty > printedQty;
  });

  if (itemsToPrint.length === 0) {
    eventBus.emit('show_mesage', {
      text: `You printed these items already on ${printerLabels[printer]}.`,
      color: 'error',
    });
    return;
  }

  // Generate token only if missing and company matches
  if (!tokenNumber && pos_profile.value.company === "Run of the Mill") {
    try {
      const response = await frappe.call({
        method: "tabrah_pos.tabrah_pos.api.posapp.get_next_token_number",
        args: {
          company: pos_profile.value.company,
          pos_profile: pos_profile.value.name,
          pos_opening_shift: pos_opening_shift.value.name
        }
      });
      if (response.message) {
        tokenNumber = response.message;
        if (!invoice_doc.value) invoice_doc.value = {};
        invoice_doc.value.custom_token_number = tokenNumber;
        // Persist to held order
        if (currentOrder) {
          currentOrder.custom_token_number = tokenNumber;
          const idx = heldOrders.findIndex(o => o.id === currentOrder.id);
          if (idx !== -1) {
            heldOrders[idx] = { ...currentOrder };
            localStorage.setItem('heldOrders', JSON.stringify(heldOrders));
          }
        }
        console.log(`Generated token number: ${tokenNumber} for Run of the Mill`);
      }
    } catch (error) {
      console.error("Error generating token number:", error);
    }
  }

  const doc = await get_invoice_doc();
  doc.grand_total = grandTotal.value;
  doc.gstAmountCash = gstAmount.value;
  doc.cover = cover.value;
  const now = new Date();
  doc.date = now.toISOString().split('T')[0];
  doc.time = now.toLocaleTimeString('en-US', { hour12: false });

  doc.kot_items = itemsToPrint.map(item => {
    let finalQty;
    const p = printedItems[item.item_code]?.[printer];
    const hasBeenPrinted = !!p;
    if (!hasBeenPrinted) {
      finalQty = item.qty;
    } else {
      const printedQty = p.qty;
      finalQty = item.qty - printedQty;
    }

let filteredBundle = item.product_bundle
      ? {
          ...item.product_bundle,
          items: filterNonJuiceBeverageBundleItems(item.product_bundle)
        }
      : undefined;
    return {
      ...item,
      qty: finalQty,
      product_bundle: filteredBundle,
    };
  });


  const groupOrder = ["hot starters", "cold starters", "sides", "breakfast", "main dishes", "deserts"];



    const groupedItems = [...doc.kot_items].sort((a, b) => {
    const groupA = (a.item_group || "").trim().toLowerCase();
    const groupB = (b.item_group || "").trim().toLowerCase();

    const indexA = groupOrder.indexOf(groupA);
    const indexB = groupOrder.indexOf(groupB);

    // DEBUG: print comparison values

    if (indexA !== -1 && indexB !== -1) return indexA - indexB;
    if (indexA === -1 && indexB !== -1) return 1;
    if (indexA !== -1 && indexB === -1) return -1;
    return groupA.localeCompare(groupB);
  });


  const printDoc = {
    ...doc,
    items: groupedItems,
    pos_profile: pos_profile.value,
  };

  // const printDoc = { 
  //   ...doc, 
  //   items: doc.kot_items,
  //   pos_profile: pos_profile.value
  // };
  if (tokenNumber) {
    printDoc.custom_token_number = tokenNumber;
  }
  // Update printedItems for this printer
  itemsToPrint.forEach(item => {
    if (!printedItems[item.item_code]) printedItems[item.item_code] = {};
    printedItems[item.item_code][printer] = {
      qty: item.qty,
      timestamp: new Date().toISOString(),
    };
  });

  holdOrder(printedItems);
  printKot(printDoc);
};
const createPreInvoice = async () => {
  if (items.value.length === 0) return;

  const doc = get_invoice_doc();

  console.log("doc-------", doc);

  // Assigning totals
  doc.grand_total = grandTotal.value;
  doc.gstAmountCash = gstAmount.value;
  doc.grand_total_card = grandTotalCard.value;
  doc.cover = cover.value; // Add cover to pre-invoice

  // Constructing cart items
  doc.cart_items = items.value.map(item => ({
    item_name:!item.bundle_doc ? item.item_name
    : !item.bundle_doc.items
      ? item.bundle_doc.item_name
      : item.bundle_doc.items.length === 0
        ? item.item_name
        : item.bundle_doc.custom_parent_item_name,
    qty: item.qty,
    rate: item.rate,
    item_group: !item.bundle_doc ? item.item_group
    : !item.bundle_doc.items
      ? item.bundle_doc.item_group
        : item.bundle_doc.items.length === 0
          ? item.item_group
            : item.bundle_doc.items[0]?.custom_item_group || item.item_group || item.custom_item_group,
    amount: item.rate * item.qty,
    bundle_items: (item.bundle_doc?.items || []).map(bundleItem => ({
      item_name: bundleItem.custom_item_name,
      rate: bundleItem.rate,
      item_group: bundleItem.custom_item_group
    }))
  }));



  // Proceed with printing and holding order
  printPreInvoice(doc);
  holdOrder();
};
const goForReturnProceed = () => {
  if (returnType.value) {
    if (returnType.value == "return") {
      submitReturn()
    }
    else {
      returnDialog.value = false
      exchangeItem.value = true
      console.log("returntype", returnType.value)
      let advancePayment = grandTotal.value
      advanceAmount.value = advancePayment
      items.value = []

    }

  }
  else {
    eventBus.emit("show_mesage", {
      text: "Please select return type",
      color: "error",
    });
  }
}
const openReturnDialog = () => {
  dialog.value = true;
};
const closeReturnDialog = () => {
  dialog.value = false;
  returnItems.value = [];
  search.value = [];
  items.value = []
  returnDialog.value = false
  advanceAmount.value = 0
  exchangeItem.value = false
  returnType.value = ''
};
const searchReturnInvoice = async () => {
  try {
    const response = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.search_invoices_for_return",
      args: {
        company: pos_profile.value.company,
        invoice_name: search.value,
      },
    });

    if (response && response.message) {
      console.log("returnItems", response);
      returnItems.value = response.message;
    }
  } catch (error) {
    console.error("Error fetching invoice document:", error);
  }
};
const loadReturn = async () => {
  returnDoc.value = returnItems.value[0];
  console.log("selected", returnDoc.value);
  dialog.value = false
  returnDoc.value.items.forEach((item) => {
    item.netTotal = item.rate * item.qty;
  })
  items.value = returnDoc.value.items
  returnDialog.value = true;

}
const submitReturn = async () => {
  submitLoading.value = true;
  const doc = returnItems.value[0];
  doc.items = items.value
  try {
    const response = await frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.create_sales_return",
      args: {
        invoice: doc,

      },
      async: true,
    });

    if (response) {
      load_print_page(response.message.return_invoice)
      eventBus.emit("show_mesage", {
        text: "Return Invoice Created Successfully",
        color: "success",
      });

      submitLoading.value = false;
      closeReturnDialog();

    }
  } catch (error) {
    console.log("error...", error);
    submitLoading.value = false;
  }
};
const load_print_page = (invoice) => {
  const print_format =
    pos_profile.value.print_format_for_online || pos_profile.value.print_format;
  const letter_head = pos_profile.value.letter_head || 0;
  const formattedValue = getFormattedPrintFormat();

  const url =
    frappe.urllib.get_base_url() +
    "/printview?doctype=Sales%20Invoice&name=" +
    invoice +
    "&trigger_print=1" +
    "&format=" +
    formattedValue +
    "&no_letterhead=" +
    letter_head;
  console.log("Print-url", url);

  const printFrame = document.getElementById("printFrame");
  printFrame.src = url;

  printFrame.onload = function () {
    printFrame.contentWindow.focus();
    printFrame.contentWindow.print();
  };
};
const getFormattedPrintFormat = () => {
  const printFormat = pos_profile.value.print_format || "";
  return encodeURIComponent(printFormat.trim());
};
const holdOrder = (printedItems = {}) => {
  if (items.value.length > 0) {
    loadingHold.value = true;

    const heldOrders = JSON.parse(localStorage.getItem("heldOrders")) || [];
    const newTable = selectedTable.value || null; // <-- current selection (may be null)

    if (holdOrderId.value) {
      const existingOrderIndex = heldOrders.findIndex(
        (order) => order.id === holdOrderId.value
      );

      if (existingOrderIndex !== -1) {
        const prevOrder = heldOrders[existingOrderIndex];
        const prevPrinted = heldOrders[existingOrderIndex].printed_items || {};
        const mergedPrinted = { ...prevPrinted, ...printedItems };

        // --- NEW: handle table transfer ---
        const prevTable = prevOrder.table || null;
        const tableChanged = prevTable !== newTable;

        if (tableChanged) {
          // free the old table (if any)
          if (prevTable) updateTableStatus(prevTable, "Available");
          // reserve the new table (if any)
          if (newTable) updateTableStatus(newTable, "Reserved");
        }


        heldOrders[existingOrderIndex] = {
          ...heldOrders[existingOrderIndex],
          items: items.value.map(item => ({ ...item, item_group: item.item_group || '' })),
          grand_total: grandTotal.value,
          timestamp: new Date().toISOString(),
          printed_items: mergedPrinted,
          cover: cover.value,
          customer: selectedCustomer.value,
          table: newTable,                     // <-- NEW: persist new table
          custom_token_number: invoice_doc.value?.custom_token_number || heldOrders[existingOrderIndex].custom_token_number || null,
        };


        // syncHeldOrderToServer(heldOrders[existingOrderIndex]);

        console.log(
          `Order updated successfully: ${heldOrders[existingOrderIndex].id}`
        );
      } else {
        console.warn(`Order with ID ${holdOrderId.value} not found.`);
      }
    } else {
      // Generate new order ID
      let nextOrderNumber = 1;

      if (heldOrders.length > 0) {
        const maxIdNumber = heldOrders.reduce((max, order) => {
          const match = order.id.match(/Hold-Order-(\d+)/);
          const number = match ? parseInt(match[1], 10) : 0;
          return number > max ? number : max;
        }, 0);

        nextOrderNumber = maxIdNumber + 1;
      }

      const nextOrderId = `Hold-Order-${nextOrderNumber}`;
      holdOrderId.value = nextOrderId; // <-- Ensure new order gets a new ID

      const employee =
        pos_profile.value.employee_list.find(
          (emp) => emp.employee === orderBy.value
        ) || {};

      const currentOrder = {
        id: nextOrderId,
        items: items.value.map(item => ({ ...item, item_group: item.item_group || '' })),
        grand_total: grandTotal.value,
        table: selectedTable.value,
        orderType: selectedOrderType.value,
        orderBy: orderBy.value,
        orderByName: employee.employee_name || "",
        timestamp: new Date().toISOString(),
        printed_items: printedItems, // Use passed printedItems for new order
        cover: cover.value,
        customer: selectedCustomer.value,
        custom_token_number: invoice_doc.value?.custom_token_number || null,
      };


      // syncHeldOrderToServer(currentOrder);

      heldOrders.push(currentOrder);
      console.log("Order held successfully:", currentOrder);

      updateTableStatus(selectedTable.value, "Reserved");
    }

    localStorage.setItem("heldOrders", JSON.stringify(heldOrders));
    items.value = [];
    cover.value = 0;
    loadingHold.value = false;
    eventBus.emit("open-product-menu");
    eventBus.emit("set-default-value");
  }
};



const updateTableStatus = async (table, status) => {
  if (table) {
    try {
      const response = await frappe.call({
        method:
          "tabrah_pos.tabrah_pos.api.posapp.update_table_status",
        args: {
          table_name: table,
          status: status
        },
      });

      if (response && response.message) {
        eventBus.emit("reserved-table", selectedTable.value);
      }
    } catch (error) {
      console.error("Error updating invoice from order:", error);
    }
  }

};
// Safe UUID (works even if window.crypto.randomUUID is unavailable)
function makeRowId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  // fallback
  return 'r-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}

async function syncHeldOrderToServer(rawHeldOrder) {

  // 1) Guard clauses
  if (!rawHeldOrder || typeof rawHeldOrder !== 'object') {
    console.warn('[syncHeldOrderToServer] no held order object provided');
    return { status: 'skipped', reason: 'no_held_order' };
  }

  // Normalize structure
  const heldOrder = {
    id: rawHeldOrder.id || null,
    table: rawHeldOrder.table || null,
    orderType: rawHeldOrder.orderType || null,
    cover: Number(rawHeldOrder.cover || 0),
    customer: rawHeldOrder.customer || null,
    custom_token_number: rawHeldOrder.custom_token_number || null,
    // ensure array
    items: Array.isArray(rawHeldOrder.items) ? rawHeldOrder.items : [],
    grand_total: Number(rawHeldOrder.grand_total || 0),
  };

  // If there are no items yet, don’t crash—still upsert header if you want, or skip:
  if (!heldOrder.items.length) {
    console.warn('[syncHeldOrderToServer] held order has no items; sending header only');
  }

  // 2) Ensure each item has a stable row_key
  heldOrder.items = heldOrder.items.map(it => ({
    ...it,
    row_key: it?.row_key || makeRowId(),
  }));

  // 3) Build payload
  const payload = {
    held_id: heldOrder.id,
    table: heldOrder.table,
    orderType: heldOrder.orderType,
    cover: heldOrder.cover,
    customer: heldOrder.customer,
    custom_token_number: heldOrder.custom_token_number,
    items: heldOrder.items.map(it => ({
      row_key: it.row_key,
      item_code: it.item_code || it.item_name,
      item_name: it.item_name,
      qty: Number(it.qty || 0),
      rate: Number(it.rate || 0),
    })),
    grand_total: heldOrder.grand_total,
  };
  try {
  // 4) Call your ERPNext method
  const res = await frappe.call({
    method: 'tabrah_pos.tabrah_pos.api.posapp.upsert_held_order',
    args: { 
    payload: payload,
    },
  });
  if (response && response.message) {
        eventBus.emit("reserved-table", selectedTable.value);
      }
    } catch (error) {
      console.error("Error updating invoice from order:", error);
    }

  // 5) Store linkage back if server returned SO name
  if (res?.message?.sales_order) {
    rawHeldOrder.sales_order = res.message.sales_order;
  }
  return res;
}

const goForPayment = async () => {
  // eventBus.emit("go-for-payment");
  if (items.value.length > 0) {
    if (saleOrder.value) {
      const invoice_doc = await processInvoiceFromOrder();
      invoice_doc.value = invoice_doc;
    } else {
      // loadingBtn.value = true;
      const doc = get_invoice_doc();
      console.log("doc-payload-ready", doc);
      invoice_doc.value = doc;
      if (!exchangeItem.value) {

        if (!selectedCustomer.value) {
          eventBus.emit("show_mesage", {
            text: `Please select customer first..`,
            color: "error",
          });
          return;
        }
        paymentProcess(invoice_doc.value);
      }
      else {
        if (grandTotal.value >= advanceAmount.value) {
          paymentProcess(invoice_doc.value);
        }
        else {
          eventBus.emit("show_mesage", {
            text: "Please select item that amount is greater than advance amount or equal",
            color: "error",
          });
        }

      }

    }
    cover.value = 0; // Clear persons field after payment
  }
};
const paymentProcess = (doc) => {
  let grandTotalValue = grandTotal.value;
  doc.total = grandTotalValue;
  doc.net_total = netTotal.value.toFixed(2);
  doc.grand_total = grandTotalValue;
  doc.rounded_total = Math.ceil(grandTotalValue);
  doc.total_taxes_and_charges = gstAmount.value.toFixed(2);
  eventBus.emit("go-for-payment");
  eventBus.emit("updated-invoice", invoice_doc.value);
};

const processInvoiceFromOrder = async () => {
  // Fetch the invoice document
  const doc = await getInvoiceFromOrderDoc();

  // Set additional discount percentage
  // doc.additional_discount_percentage = Number(additionalDiscountPercentage.value);

  // Update or create the invoice based on the presence of `doc.name`
  if (doc.name) {
    return await updateInvoiceFromOrder(doc);
  } else {
    return updateInvoiceFromOrder(doc);
  }
};
const getInvoiceFromOrderDoc = async () => {
  let doc = {};
  try {
    const response = await frappe.call({
      method:
        "tabrah_pos.tabrah_pos.api.posapp.create_sales_invoice_from_order",
      args: {
        sales_order: saleOrderDetail.value.name,
      },
    });

    if (response && response.message) {
      doc = response.message;
    }
  } catch (error) {
    console.error("Error fetching invoice document:", error);
  }

  return doc;
};
const updateInvoiceFromOrder = async (doc) => {
  try {
    const response = await frappe.call({
      method:
        "tabrah_pos.tabrah_pos.api.posapp.update_invoice_from_order",
      args: {
        data: doc,
      },
    });

    if (response && response.message) {
      invoice_doc.value = response.message;
      eventBus.emit("go-for-payment");
      eventBus.emit("updated-invoice", invoice_doc.value);
    }
  } catch (error) {
    console.error("Error updating invoice from order:", error);
  }

  return invoice_doc.value;
};

const get_invoice_doc = () => {
  let doc = {};
  if (invoice_doc.value?.name) {
    doc = { ...invoice_doc.value };
  }
  doc.doctype = "Sales Invoice";
  doc.is_pos = 1;
  doc.ignore_pricing_rule = 1;
  doc.company = doc.company || pos_profile.value.company;
  doc.pos_profile = doc.pos_profile || pos_profile.value.name;
  doc.campaign = doc.campaign || pos_profile.value.campaign;
  doc.currency = doc.currency || pos_profile.value.currency;
  doc.naming_series = doc.naming_series || pos_profile.value.naming_series;
  doc.customer = selectedCustomer.value || pos_profile.value.customer;
  doc.items = invoiceItems.value;
  doc.total = netTotal.value;
  doc.discount_amount = 0;
  doc.additional_discount_percentage = 0;
  doc.posa_pos_opening_shift = pos_opening_shift.value.name;
  doc.payments = get_payments();
  doc.taxes = [];
  doc.is_return = "";
  doc.return_against = "";
  doc.posa_offers = [];
  doc.posa_coupons = [];
  doc.posa_delivery_charges = "";
  doc.posa_delivery_charges_rate = 0;
  doc.posting_date = getCurrentDate();
  doc.table_no = selectedTable.value || "";
  doc.order_by = orderBy.value || "";
  doc.resturent_type = selectedOrderType.value;
  // doc.order_summery_for_pos = orderItems.value;
  doc.cost_center = pos_profile.value.cost_center;
  doc.custom_invoice_status = "On Hold";
  (doc.total_qty = totalQuantity.value),
    (doc.holdOrderId = holdOrderId.value ? holdOrderId.value : "");
  doc.advanceAmount = advanceAmount.value;
  doc.exchangeItem = exchangeItem.value
  doc.returnDoc = returnDoc.value
  doc.cover = cover.value; // Add cover to invoice_doc
  
  // Add token number if it was generated during KOT printing
  if (invoice_doc.value?.custom_token_number) {
    doc.custom_token_number = invoice_doc.value.custom_token_number;
  }
  
  return doc;
};
const get_payments = () => {
  const payments = [];
  // Filter payments by custom_order_type matching the selected order type
  pos_profile.value.payments
    .filter(
      (payment) => payment.custom_order_type === selectedOrderType.value
    )
    .forEach((payment) => {
      payments.push({
        amount: 0,
        mode_of_payment: payment.mode_of_payment,
        mode_type: payment.mode_type,
        default: payment.default,
        account: "",
        type: payment.mode_type,
        custom_is_exchange_mode: payment.custom_is_exchange_mode
      });
    });

  return payments;
};
// const get_payments = () => {
//   const payments = [];
//   pos_profile.value.payments.forEach((payment) => {
//     payments.push({
//       amount: 0,
//       mode_of_payment: payment.mode_of_payment,
//       default: payment.default,
//       account: "",
//     });
//   });
//   return payments;
// };
const getCurrentDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0"); // Months are zero-indexed, so we add 1
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};
const onEnterKey = (event) => {
  if (items.value.length > 0 && !loadingBtn.value) {
    goForPayment();
  }
};

const update_invoice = (doc, key, print) => {
  if (
    navigator.onLine &&
    !offlineMode.value &&
    !loadingBtn.value &&
    screen.value == 0
  ) {
    // const cleanedDoc = JSON.parse(JSON.stringify(toRaw(doc)));
    frappe.call({
      method: "tabrah_pos.tabrah_pos.api.posapp.update_invoice",
      args: {
        data: doc,
      },
      async: false,
      callback: function (r) {
        if (r.message) {
          console.log("Online Invoice draft", r.message);
          invoice_doc.value = r.message;
          invoice_doc.value.custom_invoice_status = "On Hold";
          loadingBtn.value = false;
          eventBus.emit("go-for-payment");
          eventBus.emit("updated-invoice", invoice_doc.value);
        }
      },
      error: function (requestError) {
        loadingBtn.value = false;
        console.error("Request Error: ", requestError);
        eventBus.emit("show_message", {
          text: `Something went wrong with the request..`,
          color: "error",
        });
        frappe.utils.play_sound("error");
        loadingBtn.value = false;
      },
    });
  } else {
    punching.value = "inprocess";
    let grandTotalValue = grandTotal.value;
    doc.net_total = netTotal.value.toFixed(2);
    doc.grand_total = grandTotalValue;
    doc.rounded_total = Math.ceil(grandTotalValue);
    doc.total_taxes_and_charges = gstAmount.value.toFixed(2);
    const randomReference = `${Date.now()}-${Math.floor(
      Math.random() * 10000
    )}`;
    doc.pos_referrence = randomReference;

    console.log("offline-invoice...doc", doc);
    storageService.saveUpdateInvoice(JSON.stringify(doc));
    eventBus.emit("go-for-payment");
    eventBus.emit("updated-invoice", doc);
    eventBus.emit("punching-status", punching.value);
    loadingBtn.value = false;
  }
};
const checkInternetSpeed = async (threshold = 2) => {
  const imageAddr =
    "https://upload.wikimedia.org/wikipedia/commons/a/a6/Brandenburger_Tor_abends.jpg"; // Test image URL
  const downloadSize = 2707459; // File size in bytes

  try {
    const download = new Image();
    const startTime = new Date().getTime();

    // Start downloading the test image
    const cacheBuster = `?cacheBuster=${startTime}`;
    download.src = imageAddr + cacheBuster;

    return new Promise((resolve, reject) => {
      download.onload = () => {
        const endTime = new Date().getTime();
        const duration = (endTime - startTime) / 1000; // Duration in seconds

        const bitsLoaded = downloadSize * 8; // Convert to bits
        const calculatedSpeedMbps = (
          bitsLoaded /
          duration /
          1024 /
          1024
        ).toFixed(2); // Mbps

        speedMbps.value = calculatedSpeedMbps;
        getSpeedRes.value = false;
        // if (speedMbps.value > 1) {
        //   eventBus.emit("sync-offline-invoice");
        // }

        // Update online status based on threshold
        // isInternet.value = parseFloat(calculatedSpeedMbps) >= threshold;
        // if (calculatedSpeedMbps > 2) {
        //   isInternet.value = true;
        // } else {
        //   console.log("offline mode on");
        //     isInternet.value = false;
        // }

        console.log(`Internet speed: ${calculatedSpeedMbps} Mbps.`);
        resolve({
          speedMbps: calculatedSpeedMbps,
        });
      };

      download.onerror = () => {
        speedMbps.value = null;
        console.error("Error measuring internet speed.");
        reject(new Error("Error measuring internet speed."));
      };
    });
  } catch (error) {
    console.error("Error checking internet speed:", error);
    throw error;
  }
};
const makePayloadForInvoice = () => {
  invoiceItems.value = [];

  items.value.forEach((item, index) => {
    let taxIncludeNetamount = 0;
    const total = item.rate;
    let taxrate = 1 + selectedPaymentMode.value?.tax_rate / 100 || 0;
    taxIncludeNetamount = total / taxrate;

    let taxItemWise = 0;
    let taxrateItem = 1 + item.tax_rate / 100 || 0;
    taxItemWise = total / taxrateItem;
    let customGst = 0
    customGst = total - taxItemWise



    const mainItemObject = {
      item_code: item.item_code,
      item_group: item.item_group,
      item_name: item.item_name,
      qty: item.qty,
      rate: item.rate,
      amount: item.rate,
      complementryItem: item.complementryItem,
      custom_is_complimentary_item: item.custom_is_complimentary_item,
      custom_complimentary_reason: item.custom_complimentary_reason,
      complementryLoopyItem: item.complementryLoopyItem,
      custom_is_loopy_complimentary_item: item.custom_is_loopy_complimentary_item,
      posa_notes:item.comment,
      product_bundle: item.product_bundle,
      original_rate: item.original_rate,
      // net_amount: taxIncludeNetamount,
      item_tax_template: item.tax_template,
      custom_tax_rate: item.tax_rate,
      custom_tax_amount: customGst,
      net_rate: item.rate - customGst,
      net_amount: item.rate - customGst,
      base_net_rate: item.rate - customGst,
      base_net_amount: item.rate - customGst,

    };
    invoiceItems.value.push(mainItemObject);
  });

  localStorage.setItem("order-items", JSON.stringify(invoiceItems.value));
  localStorage.setItem("net-total", JSON.stringify(netTotal.value));
  localStorage.setItem("gst-amount", JSON.stringify(gstAmount.value));

  // checkInternetSpeed();
};

const requestDeleteItem = (index) => {
  if (allowedDelete.value || !holdOrderId.value) {
    deleteItem(index);
  } else {
    pendingDeleteIndex.value = index;
    pindialog.value = true;
  }
};
const deleteItem = (index) => {
  console.log('Selected Table:',selectedTable.value)
  console.log('Before delete:', items.value.map(i => i.item_name));
  items.value.splice(index, 1);
  console.log('After delete:', items.value.map(i => i.item_name));
  // If last item was deleted, remove hold order immediately and clear fields
  if (items.value.length === 0 && holdOrderId.value) {
    const heldOrders = JSON.parse(localStorage.getItem("heldOrders")) || [];
    const orderIndex = heldOrders.findIndex(order => order.id == holdOrderId.value);
    if (orderIndex !== -1) {
      heldOrders.splice(orderIndex, 1);
      localStorage.setItem("heldOrders", JSON.stringify(heldOrders));
    }
    holdOrderId.value = '';
    items.value = [];
    cover.value = 0;
    loadingHold.value = false;
    updateTableStatus(selectedTable.value, "Available");
    eventBus.emit("open-product-menu");
    eventBus.emit("set-default-value");
  }
  makePayloadForInvoice();
  console.log('Cart items:', items.value);
};
const toggleDelete = (index) => {
  // Toggle the visibility of the delete button for the clicked item
  items.value[index].showDelete = !items.value[index].showDelete;
};

const offlineProfileData = async () => {
  try {
    const data = await storageService.getPosProfile();

    // console.log("offline pos profile from order summary", data);

    if (data && data.length > 0) {
      pos_profile.value = data[0];
      console.log("order summary OFFline profile", pos_profile.value);
      paymentModes.value = pos_profile.value.payments;
      const hasDefaultPayment = paymentModes.value.some(
        (mode) => mode.default === 1 || mode.selected
      );
      if (!hasDefaultPayment && paymentModes.value.length > 0) {
        // If no default payment mode is found, set the first mode as default
        paymentModes.value[0].default = 1;
        paymentModes.value[0].selected = true;
      }
      paymentModes.value.forEach((item) => {
        if (item.default) {
          item.selected = true;
          selectedPaymentMode.value = item;
        } else {
          item.selected = false;
        }
      });
    } else {
      console.error("No profile data found in localStorage.");
    }
  } catch (error) {
    console.error("Error getting profile:", error);
  }
};
const createSaleOrder = async (order) => {
  // if (selected.value.length > 0) {
  let invoiceDocForLoad = {};

  // Fetch the sales invoice from order
  const response = await frappe.call({
    method:
      "tabrah_pos.tabrah_pos.api.posapp.create_sales_invoice_from_order",
    args: {
      sales_order: order.name,
    },
  });

  if (response.message) {
    invoiceDocForLoad = response.message;
    // eventBus.emit("flag-for-sale-order", true);
  }

  // if (invoiceDocForLoad.items) {
  //   const selectedItems = selected.value[0].items;
  //   const loadedItems = invoiceDocForLoad.items;

  //   const loadedItemsMap = {};
  //   loadedItems.forEach((item) => {
  //     loadedItemsMap[item.item_code] = item;
  //   });

  //   // Iterate through selectedItems and update or discard items
  //   for (let i = 0; i < selectedItems.length; i++) {
  //     const selectedItem = selectedItems[i];
  //     const loadedItem = loadedItemsMap[selectedItem.item_code];

  //     if (loadedItem) {
  //       // Update the fields of selected item with loaded item's values
  //       selectedItem.qty = loadedItem.qty;
  //       selectedItem.amount = loadedItem.amount;
  //       selectedItem.uom = loadedItem.uom;
  //       selectedItem.rate = loadedItem.rate;
  //     } else {
  //       // If 'item_code' doesn't exist in loadedItems, discard the item
  //       selectedItems.splice(i, 1);
  //       i--; // Adjust the index as items are removed
  //     }
  //   }
  // }

  // Emit updated order data
  // eventBus.emit("load_order", selected.value[0]);
  // draftsDialog.value = false;

  // Call delete_sales_invoice API to delete the generated sales invoice
  await frappe.call({
    method:
      "tabrah_pos.tabrah_pos.api.posapp.delete_sales_invoice",
    args: {
      sales_invoice: invoiceDocForLoad.name,
    },
  });
  // }
};
onMounted(() => {
  // checkInternetSpeed();
  // // intervalId = setInterval(() => {
  // //   if (navigator.onLine && !getSpeedRes.value) {
  // //     getSpeedRes.value = true;
  // //     checkInternetSpeed();
  // //   }
  // // }, 8000);

  if (!navigator.onLine) {
    offlineProfileData();
  }
  eventBus.on("app-internet-status", (newStatus) => {
    offlineMode.value = !newStatus;
    offlineProfileData();
  });
  eventBus.on("set-default-value", () => {
    items.value = [];
    closeReturnDialog()
  });
  eventBus.on("exist-item-cart", (data) => {
    data.complementryItem = Boolean(data.complementryItem);
    data.complementryLoopyItem = Boolean(data.complementryLoopyItem);
    data.netTotal = data.rate * data.qty; // Ensure netTotal is always updated
    if (typeof data.index === 'number' && items.value[data.index]) {
      items.value[data.index] = { ...data };
    } else {
      // fallback: old logic
      const existingItem = items.value.find(
        (item) =>
          item.item_code === data.item_code &&
          item.complementryItem === data.complementryItem
      );
      if (existingItem) {
        Object.keys(data).forEach(key => {
          existingItem[key] = data[key];
        });
        existingItem.netTotal = existingItem.rate * existingItem.qty;
      } else {
        items.value.push({ ...data });
      }
    }
    makePayloadForInvoice();
  });

  eventBus.on("add-to-cart", (data) => {
    data.rate = data.custom_discounted_rate > 0 ? data.custom_discounted_rate : data.rate
    data.netTotal = 0;
    data.netTotal = data.rate * data.qty;
    data.complementryItem = Boolean(data.complementryItem);
    const existingItem = items.value.find(
      (item) =>
        item.item_code === data.item_code &&
        item.complementryItem === data.complementryItem
    );

    if (existingItem) {
      // Update all properties to keep in sync (including complementryItem)
      Object.keys(data).forEach(key => {
        existingItem[key] = data[key];
      });
      // If not complementary, add the new quantity
      if (!data.complementryItem) {
        existingItem.qty += data.qty;
      }
      existingItem.netTotal = existingItem.rate * existingItem.qty;
    } else {
      items.value.push({ ...data });
    }

    makePayloadForInvoice();
  });
  eventBus.on("update-table-status", (table) => {
    updateTableStatus(table, "Available")
  });


  eventBus.on("show-sale-order", (order) => {
    order.items.forEach((item) => {
      item.netTotal = item.rate * item.qty;
    });
    items.value = [];
    items.value = order.items;
    saleOrder.value = true;
    saleOrderDetail.value = order;
    createSaleOrder(order);
  });

  eventBus.on("send_pos_profile", (profile) => {
    pos_profile.value = profile;
    selectedCustomer.value = profile.customer;
    paymentModes.value = profile.payments;
    getCustomerNames(profile);
    const hasDefaultPayment = paymentModes.value.some(
      (mode) => mode.default === 1 || mode.selected
    );
    if (!hasDefaultPayment && paymentModes.value.length > 0) {
      // If no default payment mode is found, set the first mode as default
      paymentModes.value[0].default = 1;
      paymentModes.value[0].selected = true;
    }
    paymentModes.value.forEach((item) => {
      if (item.default) {
        item.selected = true;
        selectedPaymentMode.value = item;
      } else {
        item.selected = false;
      }
    });
  });
  eventBus.on("register_pos_profile", (data) => {
    pos_profile.value = data.pos_profile;
    pos_opening_shift.value = data.pos_opening_shift;
  });
  eventBus.on("set-default-value", () => {
    invoice_doc.value = {};
    saleOrder.value = false;
    saleOrderDetail.value = "";
    items.value = [];
    invoiceItems.value = [];
    holdOrderId.value = null;
    allowedDelete.value = true
    selectedCustomer.value = pos_profile.value.customer;
    eventBus.emit("selected_table", '');
  });
  eventBus.on("selected_order_type", (type) => {
    selectedOrderType.value = type;
    items.value = [];
    invoiceItems.value = [];
    invoice_doc.value = {};
  });
  eventBus.on("load-hold-order", (order) => {
    console.log("hold order", order);
    items.value = [];
    holdOrderId.value = order.id;
    eventBus.emit("open-product-menu");
    allowedDelete.value = false
    items.value = order.items;
    cover.value = order.cover || 0; // Load persons from hold order
    selectedCustomer.value = order.customer || '';
    // restore token into current invoice context
    if (!invoice_doc.value) invoice_doc.value = {};
    invoice_doc.value.custom_token_number = order.custom_token_number || '';
    eventBus.emit("selected_table", order.table || '');
    makePayloadForInvoice();
  });
  eventBus.on("current-screen", (newVal) => {
    screen.value = newVal;
  });
  eventBus.on("enter-key-called", () => {
    onEnterKey();
  });
  eventBus.on("selected_table", (table) => {
    selectedTable.value = table;
  });
  eventBus.on("order-taker", (data) => {
    orderBy.value = data;
  });


});
onUnmounted(() => {
  eventBus.off("app-internet-status");
  eventBus.off("set-default-value");
  eventBus.off("exist-item-cart");
  eventBus.off("add-to-cart");
  eventBus.off("show-sale-order");
  eventBus.off("send_pos_profile");
  eventBus.off("register_pos_profile");
  eventBus.off("set-default-value");
  eventBus.off("selected_order_type");
  eventBus.off("load-hold-order");
  eventBus.off("current-screen");
  eventBus.off("enter-key-called");
  eventBus.off("selected_table");
  eventBus.off("order-taker");
  eventBus.off("update-table-status");
});

function showAlreadyPrintedMessage() {
  eventBus.emit('show_mesage', {
    text: 'Already printed items, no new item to print found.',
    color: 'error',
  });
}
// Add a display function for customer name/number
const customerDisplay = (item) => {
  if (!item) return '';
  let name = item.customer_name || '';
  let number = item.mobile_no || '';
  if (name && number) return `${name} / ${number}`;
  if (name) return name;
  if (number) return number;
  return '';
};
// Custom filter for searching by name or number
const customerFilter = (item, queryText, itemText) => {
  const search = (queryText || '').toLowerCase();
  // Vuetify 3: itemText is an object with a 'title' property
  let displayText = '';
  if (typeof itemText === 'string') {
    displayText = itemText;
  } else if (itemText && typeof itemText === 'object' && 'title' in itemText) {
    displayText = itemText.title;
  }
  if ((displayText || '').toLowerCase().includes(search)) {
    return true;
  }
  // Also match against raw fields
  const name = (item.customer_name || '').toLowerCase();
  const number = (item.mobile_no || '').toLowerCase();
  const id = (item.name || '').toLowerCase();
  const result = name.includes(search) || number.includes(search) || id.includes(search);
  return result;
};
// Add logic to auto-select by phone number
const onCustomerSearchInput = (search) => {
  if (!search) return;
  const match = customers.value.find(
    c => c.mobile_no && c.mobile_no.toLowerCase() === search.toLowerCase()
  );
  if (match) {
    selectedCustomer.value = match.name;
  }
};
</script>

<style scoped>
.summary-main-card {
  max-height: 80vh;
  height: 80vh;
  overflow-x: hidden;
  overflow-y: auto;
  border-radius: 16px !important;
  background: #fff;
}

.order-card {
  border-radius: 12px !important;
  overflow-y: auto;
  max-height: 340px;
  height: 280px;
}

.table-header {
  font-weight: 400;
  font-size: 12px;
  font-family: 'Inter', 'Noto Sans', sans-serif;
  color: grey;
}

.item-row {
  cursor: pointer;
  transition: background 0.15s;
  border-radius: 6px;
  margin: 0 -4px;
  padding: 0 4px;
}
.item-row:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.delete-icon {
  opacity: 0.6;
  transition: opacity 0.15s, transform 0.15s;
}
.delete-icon:hover {
  opacity: 1;
  transform: scale(1.15);
}

.v-divider {
  margin: 0;
}

.payment-card {
  border-radius: 12px !important;
}

.dotted-divider {
  border-style: dashed !important;
  border-color: #D5D5D5 !important;
}

.payment-text-color {
  color: #666;
  font-size: 13px;
}

.font-20 {
  font-size: 18px;
  font-weight: 700;
}

.grand-total-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: rgba(var(--v-theme-primary), 0.06);
  border-radius: 10px;
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
}

.total-p {
  color: rgb(var(--v-theme-secondary));
  font-size: 18px;
  font-weight: 800;
}

.action-btn {
  border-radius: 10px !important;
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  letter-spacing: 0.3px !important;
}

.action-btn-primary {
  font-size: 15px !important;
  font-weight: 700 !important;
}

.payment-button {
  border-radius: 10px;
}

.payment-p {
  font-size: 16px;
  font-weight: 700;
  font-family: 'Inter', 'Archivo', sans-serif;
}

.image-container {
  text-align: center;
}

.text-decoration-underline {
  text-decoration: underline;
}

.caption {
  color: gray;
}

:deep(.v-label--clickable) {
  margin-top: 8px !important;
}

:deep(.v-select__selection-text) {
  position: relative !important;
  bottom: 8px !important;
}

@media (max-width: 600px) {
  .table-header {
    font-size: 12px;
  }

  .text-caption {
    font-size: 10px;
  }
}

.printer-btn-disabled {
  pointer-events: auto !important;
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
